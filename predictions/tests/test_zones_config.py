"""
zones_config.py - the zones of a deployment, read from storage instead of being a
literal dict in the package.

conftest stubs out the storage READ for every other test in the suite; this file is
where that read, and the parsing under it, actually get exercised.
"""

import json
import os
from unittest.mock import patch

import pytest

from crowd_predictions import zones_config
from crowd_predictions.zones_config import (ZONES, DEFAULT_LIDAR_FOV_DEGREES, Zone,
                                            ZonesNotConfigured, device_to_zone_map,
                                            lidar_coverage_multiplier, parse_zones,
                                            smartspot_location, zones_key)

TENANT_ENV = {"FIWARE_TENANT": "demo", "FIWARE_SCOPE": "/"}

PAYLOAD = {
    "Z01": {
        "name": "Plaza de prueba",
        "priority": 2,
        "location": [10.0010, 20.0010],
        "lidars": [{"id": "L1", "lat": 10.0010, "lon": 20.0010, "fov_degrees": 300.0},
                   {"id": "L2", "lat": 10.0020, "lon": 20.0020}],
        "smartspots": [{"id": "SS5", "lat": 10.0030, "lon": 20.0030}],
    },
    "Z02": {"name": "Zona sin dispositivos"},
}


class _MemoryStorage:
    def __init__(self, files=None):
        self.files = files or {}

    def download_file(self, key, path):
        if key not in self.files:
            raise FileNotFoundError(key)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.files[key])
        return path


# --- Parsing --------------------------------------------------------------------

def test_a_zone_carries_its_devices_nested_inside_it():
    """Devices live inside their zone precisely so the two cannot drift apart."""
    zones = parse_zones(PAYLOAD)
    assert set(zones) == {"Z01", "Z02"}

    z01 = zones["Z01"]
    assert isinstance(z01, Zone)
    assert z01.name == "Plaza de prueba"
    assert z01.priority == 2
    assert z01.location == (10.0010, 20.0010)
    assert z01.lidar_ids == ["L1", "L2"]
    assert z01.smartspot_ids == ["SS5"]


def test_everything_but_the_name_is_optional():
    z02 = parse_zones(PAYLOAD)["Z02"]
    assert z02.lidar_ids == [] and z02.smartspot_ids == []
    assert z02.location is None
    assert z02.priority == 1


def test_a_zone_without_a_name_falls_back_to_its_id():
    assert parse_zones({"Z09": {}})["Z09"].name == "Z09"


def test_a_device_without_an_id_is_ignored_rather_than_creating_a_nameless_one():
    zones = parse_zones({"Z01": {"name": "x", "lidars": [{"lat": 1.0}, {"id": "L7"}]}})
    assert zones["Z01"].lidar_ids == ["L7"]


def test_ids_are_read_as_strings_even_if_the_json_has_them_as_numbers():
    """The source files this format comes from number their devices (`"id": 1`),
    and every lookup downstream compares against strings."""
    zones = parse_zones({"Z01": {"name": "x", "lidars": [{"id": 1}]}})
    assert zones["Z01"].lidar_ids == ["1"]


@pytest.mark.parametrize("payload", [{}, [], "nope", None])
def test_a_payload_that_is_not_a_map_of_zones_is_rejected(payload):
    """Rejected rather than yielding an empty registry, which downstream looks
    exactly like a deployment with nothing installed."""
    with pytest.raises(ZonesNotConfigured):
        parse_zones(payload)


def test_a_zone_that_is_not_an_object_is_rejected():
    with pytest.raises(ZonesNotConfigured):
        parse_zones({"Z01": "not an object"})


# --- Reading it from storage -----------------------------------------------------

def test_the_key_is_segregated_by_tenant_and_scope():
    """Two deployments over one bucket must not read each other's zones."""
    with patch.dict(os.environ, TENANT_ENV):
        assert zones_key() == "ote/zones/demo/_/zones.json"
    with patch.dict(os.environ, {**TENANT_ENV, "FIWARE_TENANT": "otro"}):
        assert zones_key() == "ote/zones/otro/_/zones.json"


def test_no_file_in_storage_is_a_hard_failure_never_an_empty_registry(monkeypatch):
    """With no zones there is nothing to fuse, and starting empty looks exactly
    like a working run that published nothing."""
    monkeypatch.undo()   # drop conftest's stub: this is the read under test
    zones_config.reset_cache()
    with patch.dict(os.environ, TENANT_ENV), \
         patch("crowd_predictions.config.config.get_storage", return_value=_MemoryStorage()):
        with pytest.raises(ZonesNotConfigured) as excinfo:
            zones_config._load_payload()
    assert "ote/zones/demo/_/zones.json" in str(excinfo.value)


def test_a_file_that_is_not_valid_json_is_a_hard_failure_too(monkeypatch):
    monkeypatch.undo()
    zones_config.reset_cache()
    storage = _MemoryStorage({"ote/zones/demo/_/zones.json": "{ not json"})
    with patch.dict(os.environ, TENANT_ENV), \
         patch("crowd_predictions.config.config.get_storage", return_value=storage):
        with pytest.raises(ZonesNotConfigured):
            zones_config._load_payload()


def test_a_real_read_round_trips_into_the_registry(monkeypatch):
    monkeypatch.undo()
    zones_config.reset_cache()
    storage = _MemoryStorage({"ote/zones/demo/_/zones.json": json.dumps(PAYLOAD)})
    with patch.dict(os.environ, TENANT_ENV), \
         patch("crowd_predictions.config.config.get_storage", return_value=storage):
        assert set(ZONES) == {"Z01", "Z02"}
        assert ZONES["Z01"].name == "Plaza de prueba"
        assert smartspot_location("SS5") == (10.0030, 20.0030)
    zones_config.reset_cache()


# --- The cache ------------------------------------------------------------------

def test_two_tenants_in_one_process_do_not_share_zones(monkeypatch):
    """helpers/fiware_targets runs several targets in one process by mutating the
    environment. A registry cached globally would hand every target the first
    one's zones."""
    monkeypatch.undo()
    zones_config.reset_cache()
    other = {"Z99": {"name": "Zona de otro ayuntamiento"}}
    storage = _MemoryStorage({"ote/zones/demo/_/zones.json": json.dumps(PAYLOAD),
                              "ote/zones/otro/_/zones.json": json.dumps(other)})
    with patch("crowd_predictions.config.config.get_storage", return_value=storage):
        with patch.dict(os.environ, TENANT_ENV):
            assert set(ZONES) == {"Z01", "Z02"}
        with patch.dict(os.environ, {**TENANT_ENV, "FIWARE_TENANT": "otro"}):
            assert set(ZONES) == {"Z99"}
        with patch.dict(os.environ, TENANT_ENV):
            assert set(ZONES) == {"Z01", "Z02"}   # served from its own cache entry
    zones_config.reset_cache()


# --- What the rest of the code asks the registry for ------------------------------

def test_the_registry_still_reads_like_the_dict_it_replaced(monkeypatch):
    """Eleven call sites use ZONES as a mapping; that surface had to survive the
    move to storage."""
    monkeypatch.setattr(zones_config, "_load_payload", lambda: PAYLOAD)
    zones_config.reset_cache()
    assert "Z01" in ZONES
    assert len(ZONES) == 2
    assert sorted(ZONES.keys()) == ["Z01", "Z02"]
    assert {z.zone_id for z in ZONES.values()} == {"Z01", "Z02"}
    assert ZONES.get("nope") is None


def test_the_reverse_device_lookup_covers_both_kinds_of_sensor(monkeypatch):
    monkeypatch.setattr(zones_config, "_load_payload", lambda: PAYLOAD)
    zones_config.reset_cache()
    assert device_to_zone_map() == {"L1": "Z01", "L2": "Z01", "SS5": "Z01"}


def test_a_smartspot_without_coordinates_simply_has_none(monkeypatch):
    monkeypatch.setattr(zones_config, "_load_payload",
                        lambda: {"Z01": {"name": "x", "smartspots": [{"id": "SS9"}]}})
    zones_config.reset_cache()
    assert smartspot_location("SS9") is None


# --- Coverage correction, now declared per sensor in the file ---------------------

def test_each_lidar_declares_its_own_field_of_view(monkeypatch):
    """L1 declares 300 degrees, L2 declares none and takes the default 180 - the
    zone's correction is the sum, not a number we impose."""
    monkeypatch.setattr(zones_config, "_load_payload", lambda: PAYLOAD)
    zones_config.reset_cache()
    assert ZONES["Z01"].fov_by_lidar == {"L1": 300.0}
    assert lidar_coverage_multiplier("Z01") == max(1.0, 360 / (300.0 + DEFAULT_LIDAR_FOV_DEGREES))


def test_a_zone_with_no_lidar_needs_no_correction(monkeypatch):
    monkeypatch.setattr(zones_config, "_load_payload", lambda: PAYLOAD)
    zones_config.reset_cache()
    assert lidar_coverage_multiplier("Z02") == 1.0


def test_a_measured_multiplier_on_the_zone_overrides_the_formula(monkeypatch):
    """The escape hatch for when the real combined coverage is not the sum of the
    FOVs - the vendor dedupes between overlapping sensors, which the formula does
    not model."""
    payload = {"Z01": {"name": "x", "coverage_multiplier": 1.5,
                       "lidars": [{"id": "L1", "fov_degrees": 90.0}]}}   # would give x4
    monkeypatch.setattr(zones_config, "_load_payload", lambda: payload)
    zones_config.reset_cache()
    assert lidar_coverage_multiplier("Z01") == 1.5
