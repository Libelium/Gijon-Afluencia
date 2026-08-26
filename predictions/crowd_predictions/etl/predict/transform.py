"""
Generates the crowd predictions and exports one CSV per ZONE (not per hour),
with the same column convention as etl/crowd/transform.py so helpers/uploader.py
uploads them unchanged.

ONE STABLE entity id per zone with the `_pred` suffix, reused on every run - not
a new entity per predicted hour (168 hours of horizon over N zones is N
entities, not N*168).

PREDICTION_ENTITY_TYPE is PROVISIONAL: there is no official datamodel for crowd
predictions in the platform yet. It is kept as its OWN type and not CrowdFlowZone because
one is observed and the other predicted - conflating them would mean autodiscovery
(helpers/aether_history.resolve_zone_ids) has to filter our own predictions back out
of the CrowdFlowZone history, the same `_pred`-suffix guard it already needs for the
sensor-history path. Renaming PREDICTION_ENTITY_TYPE later means renaming the
entities already created.
"""

import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from crowd_predictions.config import settings
from crowd_predictions.crowd_xgboost_model import prepare_features
from crowd_predictions.helpers.aether_history import PREDICTION_ENTITY_SUFFIX
from crowd_predictions.helpers.uploader import TIMESTAMP_COLUMN, TYPE_COLUMN, URN_COLUMN
from crowd_predictions.prediction_features import predict_recursive
from crowd_predictions.training_data import feature_columns_from_train_columns

logger = logging.getLogger(__name__)


def _log_unpredicted(zone_ids: list, feature_df: pd.DataFrame, dropped: list) -> None:
    """
    Names the zones left with NO prediction, one line each.

    A zone whose lag/rolling cannot be computed gets every slot dropped and
    publishes no entity at all. That is the RIGHT behaviour - a plausible number
    computed with the features at NaN would be worse - but it is invisible: the
    platform just shows one entity fewer and nothing says which one or why.
    """
    if not dropped:
        return

    predicted = set(feature_df["zone_id"]) if not feature_df.empty else set()
    slots = Counter()
    missing = defaultdict(set)
    for record in dropped:
        slots[record["zone_id"]] += 1
        missing[record["zone_id"]].update(record.get("missing", ()))

    for zone_id in zone_ids:
        if zone_id in predicted or zone_id not in slots:
            continue
        logger.warning(
            f"NOT PUBLISHED - {zone_id}: none of its {slots[zone_id]} slots is predictable, "
            f"these features never become computable: {sorted(missing[zone_id])}. A zone needs "
            "7 days of history for lag_1w/rolling_*_7d and 28 for rolling_*_28d - expected on a "
            "newly installed zone, it resolves itself; on an old one it means it stopped reporting."
        )

    partial = {zone: slots[zone] for zone in slots if zone in predicted}
    if partial:
        logger.warning(f"Slots skipped for lack of history on zones that ARE published "
                        f"(hours, per zone): {partial}")


def _prediction_entity_id(zone_id: str) -> str:
    """
    URN of the prediction entity for a zone.

    zone_id is a full URN (CrowdFlowZone's own), and interpolating it produced a
    double-prefixed id whose `type` no longer matched the one helpers/uploader.py
    derives from the URN. Only the last segment is used; the full source id still
    goes in the `zoneId` column.
    """
    short_id = zone_id.rsplit(":", 1)[-1] if zone_id.startswith("urn:ngsi-ld:") else zone_id
    # The constant, not a literal: it is also what autodiscovery filters on, and if
    # the two drifted the model would start training on its own predictions.
    return (f"urn:ngsi-ld:{settings.prediction().PREDICTION_ENTITY_TYPE}:"
            f"{short_id}{PREDICTION_ENTITY_SUFFIX}")

def _hour_aligned_now():
    """Naive (no tz) on purpose - the whole pipeline (training_data,
    aether_history) works with naive timestamps, and mixing in an aware one
    breaks the datetime64 dtype of the column when concatenating (it turns into
    "object")."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return now.replace(minute=0, second=0, microsecond=0)

def _default_start_ts(history_bins: list, bin_minutes: int):
    """
    Starts right after the last REAL data point available, not at wall-clock
    time - if ingestion lags behind "now" even briefly, anchoring to wall-clock
    would mean lag_1d/1w find nothing and EVERY prediction is silently discarded.
    Never beyond "now" either - in case the history were more up to date than the
    clock (it should not be, but just to be safe).

    The ceiling is the hour AFTER the current one, not the current one: with an
    ingestion as fresh as the clock, the last real bin IS the current hour, and
    capping at it made the horizon start on an hour that already has a real
    measurement (seen in PRE: the first hour arrived duplicated).
    """
    if not history_bins:
        return _hour_aligned_now()
    latest = max(b["timestamp"] for b in history_bins) + timedelta(minutes=bin_minutes)
    return min(latest, _hour_aligned_now() + timedelta(minutes=bin_minutes))

def prediction_band(predicted: float, horizon_step: int, spread: dict):
    """(lower, upper) around a predicted value, or (None, None) if the model carries
    no measured band for that step.

    The band is stored RELATIVE (see crowd_xgboost_model.backtest_spread_by_horizon_step)
    because zones differ by two orders of magnitude in occupancy: a relative error is
    comparable across them AND scales itself with the predicted value here. So the
    published bounds are `predicted * (1 + lo)` and `predicted * (1 + hi)`, with lo
    usually negative and hi positive - and ASYMMETRIC on purpose, since a step where
    the model systematically under-shoots should not get a band centred on a biased
    point estimate.

    Never below 0: a negative lower bound on a headcount is nonsense."""
    step = (spread or {}).get(str(horizon_step)) or {}
    lo, hi = step.get("lo"), step.get("hi")
    if lo is None or hi is None:
        return None, None
    return max(0, round(predicted * (1 + lo))), max(0, round(predicted * (1 + hi)))


class PredictTransform:
    def __init__(self, history_bins: list, model, train_columns: list, metrics: dict = None,
                 horizon_hours: int = None, start_ts=None,
                 output_dir: str = settings.DEFAULT_PREDICTIONS_FORECAST_OUTPUT_DIR):
        self.history_bins = history_bins
        self.model = model
        self.train_columns = train_columns
        # The band measured at training time. Empty for a model trained before it
        # existed: those publish the point estimate alone, no bounds.
        self.spread = (metrics or {}).get("spread_by_horizon_step") or {}
        # The model may have been trained WITHOUT some features: the ones it
        # actually saw come from its columns sidecar, and requiring the other 15
        # would discard every predictable row.
        self.feature_columns = feature_columns_from_train_columns(train_columns)
        prediction = settings.prediction()
        self.horizon_hours = horizon_hours or prediction.PREDICTION_HORIZON_HOURS
        # An explicit start_ts (parameter or PREDICTION_START) is only for tests/backtesting -
        # in normal operation it is auto-computed in transform() from the real history.
        env_start = prediction.PREDICTION_START
        self.start_ts = start_ts or (pd.Timestamp(env_start).to_pydatetime() if env_start else None)
        self.output_dir = output_dir
        self.predictions_df = None
        self.exported_files = []

    def _predict_fn(self, feature_df: pd.DataFrame):
        """Rounded/non-negative HERE (not only when exporting) - predict_recursive
        feeds this very value back as "history" for the next step, so it has to
        be the same number that ends up published, not two different
        roundings."""
        X = prepare_features(feature_df, self.feature_columns).reindex(columns=self.train_columns, fill_value=0)
        return [max(0, round(float(v))) for v in self.model.predict(X)]

    def transform(self) -> bool:
        zone_ids = sorted({b["zone_id"] for b in self.history_bins})
        start_ts = self.start_ts or _default_start_ts(self.history_bins, bin_minutes=60)

        # predict_recursive (not build_prediction_feature_table directly): it feeds
        # each prediction back as history for the next step, the only way to go
        # beyond the ~24h ceiling (see README) - multi-day horizons refine
        # themselves over time (re-running this pipeline later replaces hours with
        # a version that has a lower horizon_step).
        logger.info(f"Predicting with the {len(self.feature_columns)} features of the stored model: "
                    f"{self.feature_columns}")
        feature_df = predict_recursive(self.history_bins, zone_ids, self._predict_fn, start_ts,
                                         horizon_hours=self.horizon_hours,
                                         feature_columns=self.feature_columns)
        _log_unpredicted(zone_ids, feature_df, feature_df.attrs.get("dropped", []))

        if feature_df.empty:
            logger.error("There is not a single predictable row (insufficient history for all slots)")
            return False

        feature_df["predictedOccupancy"] = feature_df["predicted_occupancy"]

        self.predictions_df = feature_df
        self.exported_files = self._export_csvs(feature_df)
        return True

    def _export_csvs(self, feature_df: pd.DataFrame) -> list:
        """
        ONE file (ONE entity) PER ZONE, with one row per hour of horizon; stable
        id with the `_pred` suffix, updated on every run instead of recreated.
        """
        output_path = Path(self.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        entity_type = settings.prediction().PREDICTION_ENTITY_TYPE
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        exported = []

        for zone_id, zone_df in feature_df.groupby("zone_id"):
            entity_id = _prediction_entity_id(zone_id)

            rows = []
            for _, row in zone_df.sort_values("horizon_step").iterrows():
                row_data = {
                    URN_COLUMN: entity_id,
                    TYPE_COLUMN: entity_type,
                    "zoneId": zone_id,
                    TIMESTAMP_COLUMN: row["timestamp"].strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "predictedOccupancy": row["predictedOccupancy"],
                    # How many recursive steps separate this from the last REAL data
                    # point - 1 is the most reliable (computed over real history), a
                    # high horizon_step means it leans on its own previous
                    # predictions rather than on real data - a signal of decreasing
                    # reliability for whoever consumes this.
                    "horizonStep": int(row["horizon_step"]),
                    "generatedAt": generated_at,
                }
                lower, upper = prediction_band(row["predictedOccupancy"],
                                                int(row["horizon_step"]), self.spread)
                if lower is not None:
                    row_data["predictedOccupancyLower"] = lower
                    row_data["predictedOccupancyUpper"] = upper
                rows.append(row_data)

            filepath = output_path / f"{entity_id}.csv"
            pd.DataFrame(rows).to_csv(filepath, index=False)
            exported.append(str(filepath))

        return exported
