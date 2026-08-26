"""
Transforms an aggregated Smart Spot count (peopleCount per short/medium/long
window) into the flat payload that the IoT Agent JSON expects in order to update
a CrowdFlowObserved (CFO) entity - the ONLY allowed Smart Spot entity (never
CrowdFlowEvent, which carries MAC/visitorId - see the root CLAUDE.md).

The shape is checked against a real CrowdFlowObserved entity: besides
dateObserved/peopleCount* it carries `name` (Property) and `location`
(GeoProperty), so both are emitted here.
"""

import re
import time
from typing import Optional

from crowd_predictions.config import settings
from crowd_predictions.zones_config import device_to_zone_map, smartspot_location, ZONES

# Read per call, NOT a module constant: it has to be the same type the Aether reader
# queries. A constant here would answer the default while autodiscovery asked for the
# configured one, and the mismatch shows up as "no entities discovered".

_URN_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_urn_id(device_id: str) -> str:
    s = _URN_UNSAFE.sub("_", device_id.strip()).strip("_")
    return s or "unknown"


def _default_name(device_id: str) -> str:
    """'Smart Spot <id> - <zone>' if the device is in zones_config, otherwise just the id."""
    zone_id = device_to_zone_map().get(device_id)
    if zone_id:
        return f"Smart Spot {device_id} - {ZONES[zone_id].name}"
    return f"Smart Spot {device_id}"


def transform_smartspot_observed(msg: dict, ingest_ts_ms: Optional[int] = None) -> Optional[dict]:
    """Transforms a raw aggregated Smart Spot count into a CrowdFlowObserved entity (key-values).

    Expected msg: {device_id, timestamp_ms (optional), peopleCountShortInterval,
    peopleCountMediumInterval, peopleCountLongInterval}. With no visitorid/MAC -
    this is already the aggregate, not the raw event (CFE is out of the scope of
    this transform).

    name/location are filled in automatically from zones_config.py (zone name +
    SMARTSPOT_COORDINATES) if the device_id is recognized - otherwise they are
    omitted (coordinates are never made up for an unknown device).
    """
    device_id = msg.get("device_id")
    if not device_id:
        return None

    ts_ms = msg.get("timestamp_ms")
    if ts_ms is None:
        ts_ms = ingest_ts_ms if ingest_ts_ms is not None else int(time.time() * 1000)
    ts_ms = int(ts_ms)

    entity_type = settings.aether().ENTITY_TYPE
    entity = {
        "id": f"urn:ngsi-ld:{entity_type}:{_sanitize_urn_id(device_id)}",
        "type": entity_type,
        "name": msg.get("name") or _default_name(device_id),
        "dateObserved": ts_ms // 1000,
        "peopleCountShortInterval": int(msg.get("peopleCountShortInterval", 0)),
        "peopleCountMediumInterval": int(msg.get("peopleCountMediumInterval", 0)),
        "peopleCountLongInterval": int(msg.get("peopleCountLongInterval", 0)),
        "_timeStampMs": ts_ms,  # only to derive TimeInstant in the POST, it does not go to the final body
    }

    location = smartspot_location(device_id)
    if location is not None:
        lat, lon = location
        entity["location"] = {"lat": lat, "lon": lon}

    return entity
