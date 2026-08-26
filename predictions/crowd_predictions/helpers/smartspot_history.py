"""
Current `CrowdFlowObserved` reading per Smart Spot device, for the Smart Spot side
of the fusion ETL (etl/crowd/extract.py, DATA_SOURCE=real).

AGGREGATED OVER THE SAME WINDOW THE LIDAR SIDE USES, not sampled. `CrowdFlowLidarZone`
publishes `totalConcurrentMax`: the peak of a whole hour. Reading the current value of
`peopleCountMediumInterval` instead would compare 5 minutes against 60 - and the
calibration factor IS the ratio between the two signals, so that mismatch would skew
it and then propagate to every Smart-Spot-only zone.

So the series is read and collapsed with MAX over the hour: the peak of the 5-minute
counts, which is what compares to a peak. The two are still not the same magnitude
(one is simultaneous people, the other unique devices over 5 minutes) - they never
will be, and that is precisely what the calibration factor is for. What matters is
that they cover the same window.

WHY A COUNT AND NOT RAW EVENTS. lidar_estimation.py used to receive raw detections
and count distinct `visitorid` itself. Those came from a frozen CSV export of a
development machine, which is gone. What the platform publishes is
`CrowdFlowObserved`: an already-aggregated count per device and window, with no
identities - `CrowdFlowEvent`, the one that carries MAC/visitorId, is never
published by us and is not something to be pulling into a live ETL (tens of millions
of events per quarter even for a handful of sensors, and it is personal data).

⚠️ The consequence, and it is real: summing the counts of the several Smart Spots of
one zone DOUBLE-COUNTS whoever walks past two of them. Counting distinct visitorid
did not. It is negligible for sensors far apart and it is not for two on the same
square - correct it with the zone's `coverage_multiplier` in zones.json, the same
escape hatch the overlapping-LIDAR case uses.

FRESHNESS, same as the LIDAR side: the broker keeps serving the last value it was
given for ever, so a sensor that went silent is indistinguishable from a quiet
window unless the reading's own timestamp is checked. The window asked for is derived
from that limit (lookback_hours), never configured on its own: a window shorter than
the maximum age accepted empties this side without a single error.
"""

import logging
import math
from datetime import datetime, timedelta, timezone

from crowd_predictions.config import settings
from crowd_predictions.helpers import aether
from crowd_predictions.helpers.aether_history import (BIN_MINUTES, NoHistoryError,
                                                      resolve_device_ids, time_series_to_bins)

logger = logging.getLogger(__name__)

# Minimum window to ask for, in bins: a run that fires slightly after the hour still
# finds the bin it is meant to fuse. The freshest bin per device wins.
MIN_LOOKBACK_HOURS = 3


def entity_type() -> str:
    return settings.aether().ENTITY_TYPE


def measure_id() -> str:
    return settings.aether().CROWD_MEASURE_ID


def max_age_minutes() -> float:
    """Reuses the LIDAR side's setting: both are "how old may a reading be and
    still count as this window", and two independently-edited numbers for the same
    question drift apart."""
    return settings.fusion().LIDAR_ZONE_MAX_AGE_MINUTES


def lookback_hours() -> int:
    """DERIVED, never configured: the window asked for must cover the maximum age
    accepted, or readings the freshness check would take are never fetched and the
    Smart Spot side empties in silence."""
    return max(MIN_LOOKBACK_HOURS, math.ceil(max_age_minutes() / 60.0))


def _device_id_from_entity_id(entity_id: str) -> str:
    """'urn:ngsi-ld:CrowdFlowObserved:SS5' -> 'SS5'. The devices declared in
    zones.json are the short ids, and the series comes back keyed by the full URN."""
    return entity_id.rsplit(":", 1)[-1]


def load_smartspot_counts(now: datetime = None) -> dict:
    """
    {device_id: count} for the most recent hour each Smart Spot reported, collapsed
    with MAX (see the module docstring). A device with no recent reading is simply
    absent, and lidar_estimation.py treats an absent device as no signal.

    {} on any failure - no devices discovered, an unreachable broker, an empty
    window. The caller already tolerates an empty Smart Spot side, so it degrades to
    "LIDAR-only this run" rather than taking the fusion down.
    """
    measure = measure_id()
    limit = max_age_minutes()
    lookback = lookback_hours()
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    fmt = "%Y-%m-%dT%H:%M:%S.000Z"

    try:
        device_ids = resolve_device_ids()
        df = aether.get_time_series_as_dataframe(
            device_ids=device_ids, measure_ids=[measure],
            start_date=(now - timedelta(hours=lookback)).strftime(fmt),
            end_date=now.strftime(fmt),
        )
        bins = time_series_to_bins(df, measure=measure, bin_minutes=BIN_MINUTES, agg="max")
    except NoHistoryError as e:
        logger.warning(f"No Smart Spot devices to read ({e}) - Smart Spot side of the "
                       "fusion left empty this run.")
        return {}
    except Exception as e:
        logger.exception(f"Could not read '{measure}' from the platform ({e}) - Smart Spot "
                         "side of the fusion left empty this run.")
        return {}

    freshest = {}
    for b in bins:
        device_id = _device_id_from_entity_id(str(b["device_id"]))
        if device_id not in freshest or b["timestamp"] > freshest[device_id]["timestamp"]:
            freshest[device_id] = b

    counts, stale = {}, []
    for device_id, b in freshest.items():
        age_minutes = (now - b["timestamp"]).total_seconds() / 60.0
        if limit > 0 and age_minutes > limit:
            stale.append(f"{device_id} ({b['timestamp']})")
            continue
        counts[device_id] = b["occupancy"]

    if stale:
        logger.warning(f"{len(stale)} Smart Spot reading(s) older than {limit} min - dropped: "
                       f"{stale}")
    logger.info(f"Read {len(counts)} Smart Spot(s) from the last {lookback}h of "
                f"'{measure}', collapsed hourly with max")
    return counts


def counts_from_events(events: list) -> dict:
    """{device_id: distinct visitors} from raw events - the synthetic path.

    fixtures.generate_events() produces detections with a visitorid, which is what
    the fusion used to receive. Collapsing them here keeps ONE interface into
    lidar_estimation (a count per device) whatever the source, instead of two."""
    by_device = {}
    for event in events:
        by_device.setdefault(event["device_id"], set()).add(event["visitorid"])
    return {device_id: len(visitors) for device_id, visitors in by_device.items()}
