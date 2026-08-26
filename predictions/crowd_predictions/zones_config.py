"""
The zones of a deployment and the devices installed in each one, read from
storage - NOT from this file.

    ote/zones/{tenant}/{scope}/zones.json

It used to be a literal dict with one deployment's zones and device coordinates.
That is deployment data, and hardcoding it broke every other deployment outright:
the code GATES on this registry (helpers/lidar_zone_history skips any zone_id not
in it, etl/ote publishes nothing without matching lidar ids), so another city's
real entities were all discarded while the first one's zone names were published
into its tenant.

FORMAT - one object per zone_id, devices nested inside their zone so the two can
never drift apart:

    {
      "Z01": {
        "name": "Zone 01",
        "priority": 1,
        "location": [10.0010, 20.0010],
        "lidars": [
          {"id": "L1", "lat": 10.0010, "lon": 20.0010, "fov_degrees": 300}
        ],
        "smartspots": [
          {"id": "SS5", "lat": 10.0020, "lon": 20.0020}
        ]
      }
    }

Everything except `name` is optional. `fov_degrees` per LIDAR feeds the coverage
correction (see lidar_coverage_multiplier); `coverage_multiplier` on the zone
overrides that formula outright for a zone measured in the field. No orientation:
the installed sensors are omnidirectional, so where they point is not a parameter.

DEVICE IDS ARE THE LAST SEGMENT OF THE ENTITY URN, not a readable name. The match
is by exact equality (helpers/smartspot_history._device_id_from_entity_id splits the
URN and looks the id up in the zone), so a mismatch is SILENT: the device simply
never reports and its zone degrades to the other source, or to no_data.
  - Smart Spot: `{serial}_CFO`, from `urn:ngsi-ld:CrowdFlowObserved:{serial}_CFO`.
    The same sensor's detections live under `{serial}_CFE` (CrowdFlowEvent, which
    carries identities and this repo never reads), so the suffix is part of the id.
  - LIDAR: whatever `device_id` the raw feed carries in its URL, which is what
    etl/ote publishes as `urn:ngsi-ld:CrowdFlowLidarObserved:{device_id}`.

NO max_capacity and no occupation percentage: an aforo nobody has measured is a
number that looks official and is invented. When the operator provides them, they
come back as a zone field - deliberately absent rather than defaulted.

MISSING FILE = HARD FAILURE, never a fallback. With no zones there is nothing to
fuse, and a silent empty registry looks exactly like a working run that published
nothing.

Read per (tenant, scope) and cached per pair, not globally: helpers/fiware_targets
runs several targets in one process by mutating the environment, and a registry
cached across them would give every target the first one's zones.
"""

import json
import logging
import os
import tempfile
from dataclasses import dataclass, field

from crowd_predictions.config import settings

logger = logging.getLogger(__name__)

ZONES_FILENAME = "zones.json"
# Horizontal field of view of a LIDAR that does not declare one. The installed model
# is omnidirectional (360 H x 180 V), so the default corrects nothing: a sensor with
# a narrower arc says so with its own fov_degrees. Only the horizontal arc matters -
# the vertical one does not change how much of a zone's FLOOR is covered.
DEFAULT_LIDAR_FOV_DEGREES = 360.0


@dataclass
class Zone:
    zone_id: str
    name: str
    priority: int = 1
    smartspot_ids: list = field(default_factory=list)
    lidar_ids: list = field(default_factory=list)
    location: tuple = None          # (lat, lon) centroid, or None
    coverage_multiplier: float = None   # measured in the field; overrides the formula
    fov_by_lidar: dict = field(default_factory=dict)


class ZonesNotConfigured(RuntimeError):
    """No zones.json in storage for this tenant/scope. Its own type so an entry
    point can say "this deployment is not configured yet" instead of failing later
    with an empty registry that looks like a working run."""


def zones_key() -> str:
    """ote/zones/{tenant}/{scope}/zones.json - segregated like every other key this
    repo writes, so two deployments over one bucket cannot read each other's."""
    from crowd_predictions.helpers.model_storage import segregated_key
    return segregated_key(settings.ote().OTE_ZONES_PREFIX, ZONES_FILENAME)


def _device_entries(raw: dict, key: str) -> list:
    entries = raw.get(key) or []
    return [e for e in entries if isinstance(e, dict) and e.get("id")]


def parse_zones(payload: dict) -> dict:
    """{zone_id: Zone} from the parsed JSON. Rejects a payload that is not an
    object keyed by zone_id, rather than silently yielding an empty registry."""
    if not isinstance(payload, dict) or not payload:
        raise ZonesNotConfigured(
            f"{ZONES_FILENAME} must be a non-empty JSON object keyed by zone_id, "
            f"got {type(payload).__name__}.")

    zones = {}
    for zone_id, raw in payload.items():
        if not isinstance(raw, dict):
            raise ZonesNotConfigured(f"zone '{zone_id}' is not an object.")
        lidars = _device_entries(raw, "lidars")
        smartspots = _device_entries(raw, "smartspots")
        location = raw.get("location")
        zones[zone_id] = Zone(
            zone_id=zone_id,
            name=raw.get("name") or zone_id,
            priority=raw.get("priority", 1),
            smartspot_ids=[str(d["id"]) for d in smartspots],
            lidar_ids=[str(d["id"]) for d in lidars],
            location=tuple(location) if location else None,
            coverage_multiplier=raw.get("coverage_multiplier"),
            fov_by_lidar={str(d["id"]): d["fov_degrees"] for d in lidars
                          if d.get("fov_degrees")},
        )
    return zones


def _device_coordinates(payload: dict, key: str) -> dict:
    coords = {}
    for raw in payload.values():
        for device in _device_entries(raw, key):
            if device.get("lat") is not None and device.get("lon") is not None:
                coords[str(device["id"])] = (device["lat"], device["lon"])
    return coords


def _load_payload() -> dict:
    from crowd_predictions.config.config import get_storage
    key = zones_key()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, ZONES_FILENAME)
        try:
            get_storage().download_file(key, path)
        except Exception as e:
            raise ZonesNotConfigured(
                f"No zone configuration at '{key}': {e}. This deployment cannot run "
                f"until its {ZONES_FILENAME} is uploaded - see zones_config.py for "
                "the format.") from e
        with open(path) as f:
            try:
                return json.load(f)
            except json.JSONDecodeError as e:
                raise ZonesNotConfigured(f"'{key}' is not valid JSON: {e}") from e


_CACHE = {}


def _registry() -> dict:
    """Everything parsed once per (tenant, scope): zones plus the device coordinate
    lookups, which come from the same file and would otherwise be re-read."""
    fiware = settings.fiware()
    cache_key = (fiware.FIWARE_TENANT, fiware.FIWARE_SCOPE)
    if cache_key not in _CACHE:
        payload = _load_payload()
        zones = parse_zones(payload)
        _CACHE[cache_key] = {
            "zones": zones,
            "smartspot_coordinates": _device_coordinates(payload, "smartspots"),
        }
        logger.info(f"Zones loaded for {cache_key[0]}{cache_key[1]}: {len(zones)} zone(s), "
                    f"{sum(len(z.lidar_ids) for z in zones.values())} LIDAR(s), "
                    f"{sum(len(z.smartspot_ids) for z in zones.values())} Smart Spot(s)")
    return _CACHE[cache_key]


def reset_cache() -> None:
    """Forget what was loaded. For tests, and for a long-lived process that has to
    pick up a re-uploaded zones.json without restarting."""
    _CACHE.clear()


class _ZoneRegistry:
    """Reads like the dict this module used to export (`ZONES[zone_id]`,
    `zone_id in ZONES`, `ZONES.values()`), so the eleven call sites did not have to
    change - but resolves against storage on first use, per tenant/scope."""

    def _zones(self) -> dict:
        return _registry()["zones"]

    def __getitem__(self, zone_id): return self._zones()[zone_id]
    def __contains__(self, zone_id): return zone_id in self._zones()
    def __iter__(self): return iter(self._zones())
    def __len__(self): return len(self._zones())
    def keys(self): return self._zones().keys()
    def values(self): return self._zones().values()
    def items(self): return self._zones().items()
    def get(self, zone_id, default=None): return self._zones().get(zone_id, default)
    def __repr__(self): return f"<zones: {len(self)} configured>"


ZONES = _ZoneRegistry()


def lidar_coverage_multiplier(zone_id: str) -> float:
    """Factor to multiply a zone's raw LIDAR count by, to approximate the whole
    zone and not only the arc its sensors can see.

    Summed from each LIDAR's own declared field of view, never a number we impose:
    a zone whose sensors already add up to 360 gets 1.0 by itself. A zone that
    declares `coverage_multiplier` (measured in the field) skips the formula.

    ⚠️ UNVERIFIED against real overlap: it assumes the LIDARs of a zone do NOT see
    a shared area (it sums their FOVs as if they covered separate arcs), while the
    vendor DOES dedupe detections between overlapping sensors. A multi-LIDAR zone
    with real overlap may end up double-corrected. Revisit with a real reading from
    such a zone - do not assume it holds just because nothing crashes."""
    zone = ZONES[zone_id]
    if zone.coverage_multiplier:
        return zone.coverage_multiplier
    if not zone.lidar_ids:
        return 1.0  # no LIDAR count to adjust

    total_fov = sum(zone.fov_by_lidar.get(lidar_id, DEFAULT_LIDAR_FOV_DEGREES)
                    for lidar_id in zone.lidar_ids)
    return max(1.0, 360 / total_fov) if total_fov else 1.0


def device_to_zone_map() -> dict:
    """device_id (Smart Spot or LIDAR) -> zone_id, for a fast reverse lookup."""
    return {device_id: zone.zone_id
            for zone in ZONES.values()
            for device_id in zone.smartspot_ids + zone.lidar_ids}


def smartspot_location(device_id: str):
    """(lat, lon) of a Smart Spot, or None if it declares no coordinates."""
    return _registry()["smartspot_coordinates"].get(device_id)
