"""
Daily scoring of the fused zone occupancy, the half of the vertical that feeds
itself: read the platform, score, publish the verdict on the same entity.

    CrowdFlowZone history (Aether)  ->  evaluate_batch  ->  isOutlier on CrowdFlowZone

Runs ONCE A DAY over COMPLETE days only, never the day in progress: the zones are
published hourly by the fusion CronJob, so an hourly run would score a handful of
points and could race the ingestion and see none of them. The window is the last
ANOMALY_LOOKBACK_DAYS closed days (UTC); a day already scored is scored again but
not learnt twice (the watermark in core.evaluate_batch), so a missed run is caught
up by the next one.

The verdict is published through the importation job, like the zone itself, with
the timestamp of the hour it judges. Publishing an hour twice is harmless: the
timeseries keeps the first point for (entity, attribute, time).

Only measures DECLARED in ANOMALY_CONFIG for the zone datamodel are read: unlike the
csv sweep, there is no file to auto-detect columns from, and a zone datamodel left
out of ANOMALY_CONFIG simply means this half is switched off.
"""

import logging
import os
from datetime import datetime, timedelta, timezone

import pandas as pd

from crowd_predictions.anomaly_detection.core import evaluate_batch
from crowd_predictions.config import settings
from crowd_predictions.config.config import get_storage
from crowd_predictions.helpers import aether
from crowd_predictions.helpers.aether_history import resolve_zone_ids
from crowd_predictions.helpers.uploader import (
    TIMESTAMP_COLUMN,
    TYPE_COLUMN,
    URN_COLUMN,
    upload_csv_files,
)

logger = logging.getLogger(__name__)

OUTLIER_COLUMN = "isOutlier"
# Same wire format as the zone the fusion publishes (etl/crowd/transform.py).
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def scoring_window(now: datetime = None, days: int = None) -> tuple:
    """[start, end) of the closed UTC days to score, as naive UTC datetimes."""
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    days = days or settings.anomaly().ANOMALY_LOOKBACK_DAYS
    end = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return end - timedelta(days=days), end


def zone_points(df: pd.DataFrame, measure_names: list) -> list:
    """Long Aether rows [timestamp, device_id, measure_name, value] -> one point per
    zone and instant with EVERY configured measure. An instant missing one of them is
    skipped, never filled in (see pipeline.points_from)."""
    if df.empty:
        return []

    rows = df[df["measure_name"].isin(measure_names)].copy()
    rows["value"] = pd.to_numeric(rows["value"], errors="coerce")
    stamps = pd.to_datetime(rows["timestamp"], errors="coerce", utc=True, format="mixed")
    rows["timestamp"] = stamps.dt.tz_convert("UTC").dt.tz_localize(None)
    rows = rows.dropna(subset=["timestamp", "value"])
    if rows.empty:
        return []

    wide = rows.pivot_table(index=["device_id", "timestamp"], columns="measure_name",
                            values="value", aggfunc="last").reset_index()
    present = [m for m in measure_names if m in wide.columns]
    if len(present) < len(measure_names):
        return []

    usable = wide.dropna(subset=measure_names)
    skipped = len(wide) - len(usable)
    if skipped:
        logger.warning(f"{skipped} zone reading(s) missing at least one configured measure, "
                       "skipped rather than filled in.")
    return [{"entity_id": row["device_id"],
             "raw_measures": {m: float(row[m]) for m in measure_names},
             "timestamp": row["timestamp"].to_pydatetime()}
            for _, row in usable.iterrows()]


def verdict_csvs(verdicts: dict, entity_type: str, output_dir: str) -> list:
    """One import csv per zone, `urn,type,timestamp,isOutlier`, named after its URN
    as upload_csv_files expects."""
    by_zone = {}
    for (entity_id, stamp), verdict in sorted(verdicts.items(), key=lambda kv: kv[0][1]):
        by_zone.setdefault(entity_id, []).append({
            URN_COLUMN: entity_id,
            TYPE_COLUMN: entity_type,
            TIMESTAMP_COLUMN: stamp.strftime(TIMESTAMP_FORMAT),
            OUTLIER_COLUMN: int(verdict[OUTLIER_COLUMN]),
        })

    os.makedirs(output_dir, exist_ok=True)
    paths = []
    for entity_id, rows in by_zone.items():
        path = os.path.join(output_dir, f"{entity_id}.csv")
        pd.DataFrame(rows).to_csv(path, index=False)
        paths.append(path)
    return paths


def score_zones(output_dir: str, now: datetime = None) -> int:
    """Score the closed days of every zone of the current target and publish the
    verdicts. 0 when there is nothing to do (zone datamodel not configured, no
    readings); 1 when scoring or publishing failed. No zone at all raises
    (resolve_zone_ids): with the datamodel configured, that is a deployment to fix."""
    entity_type = settings.fusion().CROWD_FLOW_ZONE_ENTITY_TYPE
    measure_names = settings.anomaly().measures_for(entity_type)
    if not measure_names:
        logger.info(f"ANOMALY_CONFIG declares no measures for '{entity_type}': daily zone "
                    "scoring is off.")
        return 0

    zone_ids = resolve_zone_ids()
    start, end = scoring_window(now)
    logger.info(f"Scoring {len(zone_ids)} zone(s) on {measure_names}, {start} -> {end}")

    df = aether.get_time_series_as_dataframe(
        device_ids=zone_ids, measure_ids=measure_names,
        start_date=start.isoformat(), end_date=end.isoformat(),
    )
    points = zone_points(df, measure_names)
    if not points:
        logger.warning(f"No complete zone readings between {start} and {end}: nothing to score.")
        return 0

    verdicts = evaluate_batch(get_storage(), entity_type, points, measure_names)
    if not verdicts:
        # evaluate_batch already logged why; with points in hand an empty result is a failure.
        return 1

    flagged = sum(1 for v in verdicts.values() if v[OUTLIER_COLUMN] == 1)
    logger.info(f"{len(verdicts)} zone hour(s) scored, {flagged} flagged as anomalous.")

    results = upload_csv_files(verdict_csvs(verdicts, entity_type, output_dir))
    return 0 if results["successful"] and not results["failed"] else 1
