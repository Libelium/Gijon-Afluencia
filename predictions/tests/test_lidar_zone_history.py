"""
Tests for helpers/lidar_zone_history.py - the snapshot read of CrowdFlowLidarZone
entities that feeds the LIDAR side of the fusion (etl/crowd/extract.py,
DATA_SOURCE=real).

NO NETWORK: requests.get is patched, same pattern as tests/test_aether.py.
"""

import os
from datetime import datetime
from unittest.mock import MagicMock, patch

from crowd_predictions.helpers.lidar_zone_history import (load_lidar_zone_counts,
                                                          load_lidar_zone_readings)

AETHER_ENV = {
    "AETHER_LINK_URL": "https://aether.example",
    "FIWARE_TENANT": "demo_tenant",
    "FIWARE_SCOPE": "/",
}


def _response(payload, status_code=200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = payload
    mock.raise_for_status.return_value = None
    return mock


def test_reads_normalized_ngsi_ld_value():
    entities = [
        {"id": "urn:ngsi-ld:CrowdFlowLidarZone:Z01",
         "type": "CrowdFlowLidarZone",
         "totalConcurrentMax": {"type": "Property", "value": 12}},
    ]
    with patch.dict(os.environ, AETHER_ENV), \
         patch("crowd_predictions.helpers.aether.requests.get", return_value=_response(entities)):
        counts = load_lidar_zone_counts()
    assert counts == {"Z01": 12}


def test_reads_plain_keyvalues_value():
    entities = [
        {"id": "urn:ngsi-ld:CrowdFlowLidarZone:Z01", "type": "CrowdFlowLidarZone",
         "totalConcurrentMax": 12},
    ]
    with patch.dict(os.environ, AETHER_ENV), \
         patch("crowd_predictions.helpers.aether.requests.get", return_value=_response(entities)):
        counts = load_lidar_zone_counts()
    assert counts == {"Z01": 12}


def test_zone_with_no_entity_is_simply_absent():
    entities = [
        {"id": "urn:ngsi-ld:CrowdFlowLidarZone:Z01", "type": "CrowdFlowLidarZone",
         "totalConcurrentMax": 5},
    ]
    with patch.dict(os.environ, AETHER_ENV), \
         patch("crowd_predictions.helpers.aether.requests.get", return_value=_response(entities)):
        counts = load_lidar_zone_counts()
    assert "Z14" not in counts  # a real zone_id, just not in this response


def test_entity_id_not_matching_a_known_zone_is_skipped():
    entities = [
        {"id": "urn:ngsi-ld:CrowdFlowLidarZone:not_a_real_zone", "type": "CrowdFlowLidarZone",
         "totalConcurrentMax": 5},
    ]
    with patch.dict(os.environ, AETHER_ENV), \
         patch("crowd_predictions.helpers.aether.requests.get", return_value=_response(entities)):
        counts = load_lidar_zone_counts()
    assert counts == {}


def test_entity_with_no_usable_attribute_is_skipped():
    entities = [
        {"id": "urn:ngsi-ld:CrowdFlowLidarZone:Z01", "type": "CrowdFlowLidarZone"},
        {"id": "urn:ngsi-ld:CrowdFlowLidarZone:Z02", "type": "CrowdFlowLidarZone",
         "totalConcurrentMax": {"type": "Property", "value": "not_a_number"}},
    ]
    with patch.dict(os.environ, AETHER_ENV), \
         patch("crowd_predictions.helpers.aether.requests.get", return_value=_response(entities)):
        counts = load_lidar_zone_counts()
    assert counts == {}


def test_never_reads_totalcount_afluencia_instead_of_the_concurrent_one():
    """aforo != afluencia (see lidar_estimation.py) - totalCount must not leak in
    even if it is the only attribute present."""
    entities = [
        {"id": "urn:ngsi-ld:CrowdFlowLidarZone:Z01", "type": "CrowdFlowLidarZone",
         "totalCount": 300},
    ]
    with patch.dict(os.environ, AETHER_ENV), \
         patch("crowd_predictions.helpers.aether.requests.get", return_value=_response(entities)):
        counts = load_lidar_zone_counts()
    assert counts == {}


def test_custom_entity_type_and_attribute_are_honoured():
    entities = [
        {"id": "urn:ngsi-ld:OtroTipo:Z01", "type": "OtroTipo", "otroAtributo": 7},
    ]
    env = {**AETHER_ENV, "LIDAR_ZONE_ENTITY_TYPE": "OtroTipo",
           "LIDAR_ZONE_CONCURRENT_ATTR": "otroAtributo"}
    with patch.dict(os.environ, env), \
         patch("crowd_predictions.helpers.aether.requests.get", return_value=_response(entities)) as get:
        counts = load_lidar_zone_counts()
    assert counts == {"Z01": 7}
    assert get.call_args.kwargs["params"]["types"] == "OtroTipo"


def test_broker_unreachable_returns_empty_instead_of_raising():
    """CrowdExtract already tolerates an empty lidar_zone_counts (falls back to
    Smart Spot) - an unreachable broker must degrade, not crash the fusion run."""
    with patch.dict(os.environ, AETHER_ENV), \
         patch("crowd_predictions.helpers.aether.requests.get", side_effect=Exception("boom")):
        counts = load_lidar_zone_counts()
    assert counts == {}


# --- Freshness. The broker serves the last value it was given for ever, so
# --- without this a stopped upstream ETL is invisible.

NOW = datetime(2026, 8, 12, 12, 0)


def _entity(zone_id: str, value: int, observed_at: str = None) -> dict:
    attr = {"type": "Property", "value": value}
    if observed_at:
        attr["observedAt"] = observed_at
    return {"id": f"urn:ngsi-ld:CrowdFlowLidarZone:{zone_id}",
            "type": "CrowdFlowLidarZone", "totalConcurrentMax": attr}


def test_a_stale_reading_is_dropped_so_the_zone_falls_back_instead_of_freezing():
    """The bug this prevents: the upstream ETL dies, the broker keeps serving its
    last value, and the fusion publishes a frozen aforo as confidence='measured'."""
    entities = [_entity("Z01", 12, "2026-08-12T11:55:00Z"),   # 5 min old
                _entity("Z02", 99, "2026-08-11T12:00:00Z")]   # a day old
    with patch.dict(os.environ, AETHER_ENV), \
         patch("crowd_predictions.helpers.aether.requests.get", return_value=_response(entities)):
        counts = load_lidar_zone_counts(now=NOW)
    assert counts == {"Z01": 12}


def test_the_max_age_is_configurable_and_zero_disables_the_check():
    entities = [_entity("Z01", 12, "2026-08-11T12:00:00Z")]
    with patch.dict(os.environ, {**AETHER_ENV, "LIDAR_ZONE_MAX_AGE_MINUTES": "0"}), \
         patch("crowd_predictions.helpers.aether.requests.get", return_value=_response(entities)):
        assert load_lidar_zone_counts(now=NOW) == {"Z01": 12}


def test_a_reading_with_no_timestamp_at_all_is_kept_rather_than_blanking_the_lidar_side():
    """Whether the broker answers normalized or keyValues is still unconfirmed - a
    keyValues payload carries no observedAt, and failing closed there would silently
    disable the whole LIDAR half of the fusion."""
    entities = [{"id": "urn:ngsi-ld:CrowdFlowLidarZone:Z01",
                 "type": "CrowdFlowLidarZone", "totalConcurrentMax": 12}]
    with patch.dict(os.environ, AETHER_ENV), \
         patch("crowd_predictions.helpers.aether.requests.get", return_value=_response(entities)):
        assert load_lidar_zone_counts(now=NOW) == {"Z01": 12}


def test_the_entity_level_timestamp_is_used_when_the_attribute_has_none():
    entities = [{"id": "urn:ngsi-ld:CrowdFlowLidarZone:Z01", "type": "CrowdFlowLidarZone",
                 "modifiedAt": "2026-08-11T12:00:00Z", "totalConcurrentMax": 12}]
    with patch.dict(os.environ, AETHER_ENV), \
         patch("crowd_predictions.helpers.aether.requests.get", return_value=_response(entities)):
        assert load_lidar_zone_counts(now=NOW) == {}


def test_readings_carry_when_they_were_taken_for_the_isstale_watchdog():
    entities = [_entity("Z01", 12, "2026-08-12T11:55:00Z")]
    with patch.dict(os.environ, AETHER_ENV), \
         patch("crowd_predictions.helpers.aether.requests.get", return_value=_response(entities)):
        readings = load_lidar_zone_readings(now=NOW)
    assert readings["Z01"]["value"] == 12
    assert readings["Z01"]["observed_at"] == datetime(2026, 8, 12, 11, 55)
