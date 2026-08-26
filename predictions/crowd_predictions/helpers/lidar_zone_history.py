"""
Latest `CrowdFlowLidarZone` reading per zone, for the LIDAR side of the fusion ETL
(etl/crowd/extract.py, DATA_SOURCE=real). These entities are published by an ETL
OUTSIDE this repo that reconstructs presence
segments from the raw LIDAR feed and aggregates per zone/window - this module only
reads their current value, it does not compute anything.

A SNAPSHOT read, not a time series: unlike helpers/aether_history.py (which manages
months of training history across three different windows), lidar_estimation.py
only ever needs the CURRENT count per zone for the run it is fusing right now - the
same shape fixtures.generate_lidar_zone_counts() already returns for the synthetic
path. That is why this lives in its own small module instead of inside
aether_history.py.

Reads `LIDAR_ZONE_CONCURRENT_ATTR` (default totalConcurrentMax) and NEVER totalCount:
aforo (simultaneous), not afluencia (cumulative) - see
the aforo/afluencia note in lidar_estimation.py's module docstring.

FRESHNESS IS PART OF THE READ. The broker keeps serving the last value it was
given for ever, so a STOPPED upstream ETL is indistinguishable from a quiet window
unless the reading's own timestamp is checked - and the fusion would go on
publishing a frozen occupancy as confidence="measured", which is the exact failure
zone_estimate()'s "no_data" case exists to avoid. Readings older than
LIDAR_ZONE_MAX_AGE_MINUTES are dropped and their zone falls back to Smart Spot.

⚠️ NOT YET VERIFIED against a real broker response: whether get_entities_by_type()
returns attribute values normalized ({"type": "Property", "value": N, "observedAt":
...}) or as keyValues (N directly) is assumed defensively below (both are handled),
not confirmed. Fix _read_concurrent_value() once a real payload is seen. A reading
whose timestamp cannot be determined AT ALL is kept, with a warning: a keyValues
broker would otherwise blank the whole LIDAR side of the fusion.
"""

import logging
from datetime import datetime, timezone

from crowd_predictions.config import settings
from crowd_predictions.helpers import aether
from crowd_predictions.zones_config import ZONES

logger = logging.getLogger(__name__)

# Where a timestamp for the reading may live, most specific first: the attribute's
# own observedAt, then the entity-level ones.
OBSERVED_AT_KEYS = ("observedAt", "modifiedAt", "createdAt")


def entity_type() -> str:
    return settings.fusion().LIDAR_ZONE_ENTITY_TYPE


def concurrent_attr() -> str:
    return settings.fusion().LIDAR_ZONE_CONCURRENT_ATTR


def max_age_minutes() -> float:
    return settings.fusion().LIDAR_ZONE_MAX_AGE_MINUTES


def _parse_timestamp(raw):
    """ISO-8601 (with or without a trailing 'Z') -> naive UTC datetime, the
    convention everywhere in this repo. None if it is not parseable."""
    if not isinstance(raw, str):
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc).replace(tzinfo=None) if parsed.tzinfo else parsed


def _read_observed_at(entity: dict, attr: str):
    """When the reading was taken: the attribute's own observedAt first, the
    entity-level timestamps as a fallback. None if the payload carries none."""
    raw_attr = entity.get(attr)
    sources = ([raw_attr] if isinstance(raw_attr, dict) else []) + [entity]
    for source in sources:
        for key in OBSERVED_AT_KEYS:
            parsed = _parse_timestamp(source.get(key))
            if parsed is not None:
                return parsed
    return None


def _zone_id_from_entity_id(entity_id: str) -> str:
    """'urn:ngsi-ld:CrowdFlowLidarZone:Z03' -> 'Z03' - the segment after the last
    ':', same convention as smartspot_transform._sanitize_urn_id's stable id."""
    return entity_id.rsplit(":", 1)[-1]


def _read_concurrent_value(entity: dict, attr: str):
    """The attribute value, normalized-NGSI-LD or keyValues (see the module
    docstring - not confirmed against a real response yet). None if absent or of
    an unexpected shape, rather than guessing a number."""
    raw = entity.get(attr)
    if isinstance(raw, dict) and "value" in raw:
        raw = raw["value"]
    if isinstance(raw, (int, float)):
        return raw
    return None


def load_lidar_zone_readings(now: datetime = None) -> dict:
    """
    {zone_id: {"value": simultaneous_count, "observed_at": naive datetime|None}}
    for every zone with a CURRENT CrowdFlowLidarZone reading. A zone with no entity
    yet (not deployed, no data this window) or with a reading older than
    LIDAR_ZONE_MAX_AGE_MINUTES is simply absent - lidar_estimation.py already treats
    an absent zone as "no LIDAR reading this window" (falls back to Smart Spot).

    {} on a broker error - the caller (CrowdExtract) already tolerates an empty
    LIDAR side, so an unreachable broker degrades to "Smart-Spot-only this run",
    not a crash.
    """
    etype = entity_type()
    attr = concurrent_attr()
    limit = max_age_minutes()
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)

    entities = aether.get_entities_by_type([etype])
    if entities is None:
        logger.error(f"Could not query the broker for entities of type '{etype}' "
                     "(see the error above) - LIDAR side of the fusion left empty this run.")
        return {}

    readings, undated, stale = {}, [], []
    for entity in entities:
        entity_id = entity.get("id")
        if not entity_id:
            continue
        zone_id = _zone_id_from_entity_id(entity_id)
        if zone_id not in ZONES:
            logger.warning(f"'{entity_id}' does not match any known zone_id - skipped")
            continue
        value = _read_concurrent_value(entity, attr)
        if value is None:
            logger.warning(f"'{entity_id}' has no usable '{attr}' - skipped")
            continue

        observed_at = _read_observed_at(entity, attr)
        if observed_at is None:
            undated.append(entity_id)
        elif limit > 0 and (now - observed_at).total_seconds() / 60.0 > limit:
            stale.append(f"{entity_id} ({observed_at})")
            continue
        readings[zone_id] = {"value": value, "observed_at": observed_at}

    if undated:
        logger.warning(f"{len(undated)} LIDAR zone reading(s) carry no timestamp - accepted "
                       f"WITHOUT a freshness check: {undated}")
    if stale:
        logger.warning(f"{len(stale)} LIDAR zone reading(s) older than {limit} min - dropped, "
                       f"their zones fall back to Smart Spot: {stale}")
    logger.info(f"Read {len(readings)}/{len(ZONES)} zone(s) with a current '{attr}' "
                f"from '{etype}' entities")
    return readings


def load_lidar_zone_counts(now: datetime = None) -> dict:
    """{zone_id: simultaneous_count} - load_lidar_zone_readings() without the
    timestamps, which is the shape lidar_estimation.py consumes."""
    return {zone_id: r["value"] for zone_id, r in load_lidar_zone_readings(now).items()}
