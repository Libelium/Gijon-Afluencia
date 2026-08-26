"""
Tests for the Aether Link client and for the conversion of its response into the
occupancy bins that training_data.py consumes.

NO NETWORK: requests.post / requests.get are patched. The fixtures below are the
REAL responses a live environment returned, trimmed in length but not in shape -
that is the point of hardcoding them rather than inventing a plausible payload.
"""

import math
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from crowd_predictions.helpers import aether
from crowd_predictions.helpers.aether_history import (
    COLD_START_DAYS, LAG_HARD_MINIMUM_DAYS, PREDICTION_ENTITY_SUFFIX, ROLLING_WARMUP_DAYS,
    NoHistoryError, history_window, incremental_train_days, incremental_training_window_hours,
    incremental_window_hours, load_history_bins, minimum_window_hours, resolve_device_ids,
    resolve_zone_ids, time_series_to_bins,
)
from crowd_predictions.training_data import DEFAULT_ROLLING_MIN_COVERAGE

AETHER_ENV = {
    "AETHER_LINK_URL": "https://aether-link.example",
    "FIWARE_TENANT": "libelium",
    "FIWARE_SCOPE": "/",
}

# Real response of POST /api/v1/time-series (PRE, 2026-08-03).
TIMESERIES_RESPONSE = [{
    "time_series": [{
        "device_id": "urn:ngsi-ld:CrowdFlowObserved:Barcelona_Crowd_1",
        "measure_id": "peopleCountMediumInterval",
        "values": [
            {"timestamp": "2025-11-26T00:00:00", "value": 15.0},
            {"timestamp": "2025-11-26T01:00:00", "value": 13.0},
            {"timestamp": "2025-11-26T02:00:00", "value": 13.0},
        ],
    }],
    "options": {"start_date": "2025-11-01T00:00:00Z", "end_date": "2026-08-03T00:00:00Z",
                "limit": 5, "tenant": "libelium", "scope": "/"},
}]

EMPTY_TIMESERIES_RESPONSE = [{
    "time_series": [],
    "options": {"tenant": "libelium", "scope": "tenant_a"},
}]

# Real response of GET /api/v1/context-broker/entities?types=CrowdFlowObserved
# (PRE, 2026-08-03), trimmed to the fields the code looks at.
ENTITIES_RESPONSE = [
    {"id": "urn:ngsi-ld:CrowdFlowObserved:Barcelona_Crowd_1", "type": "CrowdFlowObserved"},
    {"id": "urn:ngsi-ld:CrowdFlowObserved:Barcelona_Crowd_2", "type": "CrowdFlowObserved"},
    {"id": "urn:ngsi-ld:CrowdFlowObserved:Barcelona_Crowd_3", "type": "CrowdFlowObserved"},
]


def _response(payload, status_code=200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = payload
    mock.raise_for_status.return_value = None
    return mock


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

def test_missing_url_is_a_clear_configuration_error_not_a_traceback():
    with patch.dict(os.environ, {"AETHER_LINK_URL": "", "FIWARE_TENANT": "libelium",
                                  "FIWARE_SCOPE": "/"}):
        ok, message = aether.validate_aether_config()
        assert ok is False
        assert "AETHER_LINK_URL" in message
        with pytest.raises(aether.AetherConfigError, match="AETHER_LINK_URL"):
            aether.raise_for_aether_config()


def test_tenant_and_scope_come_from_the_fiware_variables_not_from_aether_ones():
    """The decision behind reusing FIWARE_TENANT/FIWARE_SCOPE: one single pair, so
    it is impossible to read the history from one scope and publish the
    predictions into another. AETHER_TENANT/AETHER_SCOPE must be ignored."""
    with patch.dict(os.environ, {**AETHER_ENV, "FIWARE_TENANT": "libelium",
                                  "FIWARE_SCOPE": "tenant_a", "AETHER_TENANT": "otro",
                                  "AETHER_SCOPE": "otro_scope"}):
        assert aether.aether_tenant() == "libelium"
        assert aether.aether_scope() == "tenant_a"


def test_configuration_is_read_at_call_time_so_tests_can_patch_it():
    with patch.dict(os.environ, {"AETHER_LINK_URL": "https://a/"}):
        assert aether.aether_url() == "https://a"
    with patch.dict(os.environ, {"AETHER_LINK_URL": "https://b"}):
        assert aether.aether_url() == "https://b"


def test_parse_relative_date_normalizes_the_accepted_formats():
    assert aether.parse_relative_date("2025-12-31T23:00:00.000Z") == "2025-12-31T23:00:00.000Z"
    assert aether.parse_relative_date("2025-12-31T23:00:00") == "2025-12-31T23:00:00.000Z"
    assert aether.parse_relative_date("2025-12-31 23:00:00") == "2025-12-31T23:00:00.000Z"
    assert aether.parse_relative_date("2025-12-31") == "2025-12-31T00:00:00.000Z"


def test_parse_relative_date_rejects_garbage():
    with pytest.raises(ValueError):
        aether.parse_relative_date("last tuesday")


# --------------------------------------------------------------------------
# The time-series request
# --------------------------------------------------------------------------

def test_time_series_request_is_sent_as_a_list_with_tenant_and_scope_in_options():
    """Both halves are contract, not style: the endpoint rejects a bare object,
    and without tenant/scope in "options" it answers an empty series (verified
    against a live environment: the same query with another scope comes back empty)."""
    with patch.dict(os.environ, AETHER_ENV), \
         patch("crowd_predictions.helpers.aether.requests.post", return_value=_response(TIMESERIES_RESPONSE)) as post:
        aether.get_time_series(["dev1"], ["peopleCountMediumInterval"],
                               "2025-11-01T00:00:00.000Z", "2026-08-03T00:00:00.000Z", limit=5)

    body = post.call_args.kwargs["json"]
    assert isinstance(body, list) and len(body) == 1
    request = body[0]
    assert request["device_ids"] == ["dev1"]
    assert request["measure_ids"] == ["peopleCountMediumInterval"]
    assert request["options"]["tenant"] == "libelium"
    assert request["options"]["scope"] == "/"
    assert request["options"]["limit"] == 5
    assert post.call_args.args[0].endswith("/api/v1/time-series")


def test_time_series_limit_falls_back_to_the_environment_variable():
    with patch.dict(os.environ, {**AETHER_ENV, "AETHER_TIMESERIES_LIMIT": "123"}), \
         patch("crowd_predictions.helpers.aether.requests.post", return_value=_response(TIMESERIES_RESPONSE)) as post:
        aether.get_time_series(["dev1"], ["m"], "2025-11-01", "2026-08-03")

    assert post.call_args.kwargs["json"][0]["options"]["limit"] == 123


def test_time_series_returns_the_first_element_of_the_list_response():
    with patch.dict(os.environ, AETHER_ENV), \
         patch("crowd_predictions.helpers.aether.requests.post", return_value=_response(TIMESERIES_RESPONSE)):
        result = aether.get_time_series(["dev1"], ["m"], "2025-11-01", "2026-08-03")

    assert result["time_series"][0]["measure_id"] == "peopleCountMediumInterval"


def test_time_series_returns_none_on_a_transport_error():
    """None means "the request failed", which is a different situation from "it
    worked and there is nothing" (an empty time_series) - the caller reacts
    differently to each."""
    import requests as requests_module

    with patch.dict(os.environ, AETHER_ENV), \
         patch("crowd_predictions.helpers.aether.requests.post", side_effect=requests_module.exceptions.Timeout):
        assert aether.get_time_series(["dev1"], ["m"], "2025-11-01", "2026-08-03") is None


def test_dataframe_has_the_expected_columns():
    with patch.dict(os.environ, AETHER_ENV), \
         patch("crowd_predictions.helpers.aether.requests.post", return_value=_response(TIMESERIES_RESPONSE)):
        df = aether.get_time_series_as_dataframe(["dev1"], ["peopleCountMediumInterval"],
                                                 "2025-11-01", "2026-08-03")

    assert list(df.columns) == ["timestamp", "device_id", "measure_name", "value"]
    assert len(df) == 3
    assert df["timestamp"].iloc[0] == pd.Timestamp("2025-11-26T00:00:00")


def test_an_empty_response_does_not_blow_up_and_gives_an_empty_dataframe():
    with patch.dict(os.environ, AETHER_ENV), \
         patch("crowd_predictions.helpers.aether.requests.post",
               return_value=_response(EMPTY_TIMESERIES_RESPONSE)):
        df = aether.get_time_series_as_dataframe(["dev1"], ["m"], "2025-11-01", "2026-08-03")

    assert df.empty


def test_a_none_response_does_not_blow_up_either():
    assert aether.time_series_to_dataframe(None).empty
    assert aether.time_series_to_dataframe({}).empty


# --------------------------------------------------------------------------
# Aether response -> the bins that training_data.py expects
# --------------------------------------------------------------------------

def test_conversion_produces_the_shape_the_feature_functions_expect():
    """The shape training_data.py expects, so add_calendar_features() /
    add_lag_features() / add_rolling_features() work with training_data.py
    untouched."""
    df = pd.DataFrame([
        {"timestamp": pd.Timestamp("2025-11-26T00:00:00"), "device_id": "S1",
         "measure_name": "peopleCountMediumInterval", "value": 15.0},
        {"timestamp": pd.Timestamp("2025-11-26T01:00:00"), "device_id": "S1",
         "measure_name": "peopleCountMediumInterval", "value": 13.0},
    ])

    bins = time_series_to_bins(df, measure="peopleCountMediumInterval")

    assert bins == [
        {"device_id": "S1", "timestamp": datetime(2025, 11, 26, 0, 0), "occupancy": 15},
        {"device_id": "S1", "timestamp": datetime(2025, 11, 26, 1, 0), "occupancy": 13},
    ]
    # Same keys, in the same types, as the CSV loader.
    assert set(bins[0]) == {"device_id", "timestamp", "occupancy"}
    assert isinstance(bins[0]["occupancy"], int)
    assert bins[0]["timestamp"].tzinfo is None  # naive, like the rest of the pipeline


def test_the_converted_bins_feed_training_data_without_touching_it():
    """End-to-end over the real shape: 40 days of hourly bins built out of an
    Aether response must come out the other side of add_calendar_features ->
    add_lag_features -> add_rolling_features with the feature columns filled."""
    from crowd_predictions.training_data import (FEATURE_COLUMNS, add_calendar_features,
                                add_lag_features, add_rolling_features)

    rows = []
    base = pd.Timestamp("2026-01-01T00:00:00")
    for day in range(40):
        for hour in range(24):
            rows.append({"timestamp": base + pd.Timedelta(days=day, hours=hour),
                          "device_id": "urn:ngsi-ld:CrowdFlowObserved:Device_1",
                          "measure_name": "peopleCountMediumInterval",
                          "value": float(10 + hour)})

    bins = time_series_to_bins(pd.DataFrame(rows), measure="peopleCountMediumInterval",
                               id_column="zone_id")
    df = add_rolling_features(add_lag_features(add_calendar_features(bins)))
    usable = df.dropna(subset=FEATURE_COLUMNS)

    assert not usable.empty
    # MEASURED, not assumed. The cliff of dropna() over the 15 features is
    # rolling_*_28d, not lag_1w (7 days): the rolling window needs 75% of its 28 days
    # present, i.e. 21. That is why the reading window floor is 28 days and not 7.
    first_usable_day = math.ceil(DEFAULT_ROLLING_MIN_COVERAGE * ROLLING_WARMUP_DAYS)
    assert first_usable_day == 21
    assert usable["timestamp"].min() == base + pd.Timedelta(days=first_usable_day)
    assert 24 * (40 - first_usable_day) == len(usable)


def test_rolling_28d_goes_nan_with_little_history_instead_of_degrading_silently():
    """The reason for the 28-day floor of the reading window. add_rolling_features()
    USED TO compute over whatever days of the last 28 existed, so with a short window
    rolling_mean_28d was not NaN (nothing failed) - it was simply a different feature
    from the one the model had been trained on. Now it is NaN and the feature drops
    out of the set, which is loud instead of silent."""
    from crowd_predictions.training_data import (add_calendar_features, add_lag_features,
                                add_rolling_features)

    def _rolling_mean_at(n_days, target_day):
        rows = [{"timestamp": pd.Timestamp("2026-01-01") + pd.Timedelta(days=d, hours=12),
                  "device_id": "S1", "measure_name": "m", "value": float(d)}
                 for d in range(n_days)]
        bins = time_series_to_bins(pd.DataFrame(rows), measure="m", id_column="zone_id")
        df = add_rolling_features(add_lag_features(add_calendar_features(bins)))
        row = df[df["timestamp"] == pd.Timestamp("2026-01-01") + pd.Timedelta(days=target_day, hours=12)]
        return row["rolling_mean_28d"].iloc[0]

    short_window = _rolling_mean_at(n_days=10, target_day=9)   # only 9 past days exist
    full_window = _rolling_mean_at(n_days=40, target_day=37)   # 28 real past days exist

    assert pd.isna(short_window)   # no partial mean pretending to be a 28-day one
    assert pd.notna(full_window)


def test_conversion_floors_off_the_hour_readings_onto_the_bin():
    """A measurement at HH:07 would otherwise produce a row whose lag_1d/1w
    lookups (by EXACT timestamp) never match anything."""
    df = pd.DataFrame([
        {"timestamp": pd.Timestamp("2025-11-26T00:07:00"), "device_id": "S1",
         "measure_name": "m", "value": 5.0},
    ])
    bins = time_series_to_bins(df, measure="m")
    assert bins[0]["timestamp"] == datetime(2025, 11, 26, 0, 0)


def test_conversion_collapses_two_readings_in_the_same_hour_into_their_MEAN():
    """Two rows with the same (device_id, timestamp) key would leave one of the
    duplicates out of the lag index at random, so they must collapse - and they
    collapse into the MEAN: peopleCount* counts people over a window of minutes, so
    the last reading of the hour describes its final minutes, not the hour.
    ("last" is right for state-change data like a parking spot, not for this.)"""
    df = pd.DataFrame([
        {"timestamp": pd.Timestamp("2025-11-26T00:10:00"), "device_id": "S1",
         "measure_name": "m", "value": 5.0},
        {"timestamp": pd.Timestamp("2025-11-26T00:50:00"), "device_id": "S1",
         "measure_name": "m", "value": 9.0},
    ])
    bins = time_series_to_bins(df, measure="m")
    assert bins == [{"device_id": "S1", "timestamp": datetime(2025, 11, 26, 0, 0),
                     "occupancy": 7}]   # mean(5, 9), not 9


def test_conversion_rounds_instead_of_truncating():
    df = pd.DataFrame([
        {"timestamp": pd.Timestamp("2025-11-26T00:00:00"), "device_id": "S1",
         "measure_name": "m", "value": 14.7},
    ])
    assert time_series_to_bins(df, measure="m")[0]["occupancy"] == 15


def test_conversion_drops_the_timezone_when_the_platform_sends_one():
    df = pd.DataFrame([
        {"timestamp": pd.Timestamp("2025-11-26T10:00:00+00:00"), "device_id": "S1",
         "measure_name": "m", "value": 3.0},
    ])
    bins = time_series_to_bins(df, measure="m")
    assert bins[0]["timestamp"] == datetime(2025, 11, 26, 10, 0)
    assert bins[0]["timestamp"].tzinfo is None


def test_conversion_of_another_measure_yields_nothing_instead_of_mixing_measures():
    df = pd.DataFrame([
        {"timestamp": pd.Timestamp("2025-11-26T00:00:00"), "device_id": "S1",
         "measure_name": "peopleCountShortInterval", "value": 3.0},
    ])
    assert time_series_to_bins(df, measure="peopleCountMediumInterval") == []


def test_conversion_of_an_empty_dataframe_returns_an_empty_list():
    assert time_series_to_bins(pd.DataFrame()) == []


# --------------------------------------------------------------------------
# Autodiscovery of sensors
# --------------------------------------------------------------------------

def test_explicit_device_ids_win_over_autodiscovery():
    with patch.dict(os.environ, {**AETHER_ENV, "DEVICE_IDS": "A, B ,C"}), \
         patch("crowd_predictions.helpers.aether.requests.get") as get:
        assert resolve_device_ids() == ["A", "B", "C"]
    get.assert_not_called()  # the broker is not even queried


def test_autodiscovery_asks_the_broker_for_the_entity_type():
    with patch.dict(os.environ, {**AETHER_ENV, "DEVICE_IDS": ""}), \
         patch("crowd_predictions.helpers.aether.requests.get", return_value=_response(ENTITIES_RESPONSE)) as get:
        discovered = resolve_device_ids()

    assert discovered == [
        "urn:ngsi-ld:CrowdFlowObserved:Barcelona_Crowd_1",
        "urn:ngsi-ld:CrowdFlowObserved:Barcelona_Crowd_2",
        "urn:ngsi-ld:CrowdFlowObserved:Barcelona_Crowd_3",
    ]
    assert get.call_args.kwargs["params"] == {"types": "CrowdFlowObserved",
                                              "limit": 1000, "offset": 0}
    # tenant/scope travel as headers on this endpoint, not in the body.
    assert get.call_args.kwargs["headers"] == {"tenant": "libelium", "scope": "/"}


def test_autodiscovery_excludes_our_own_prediction_entities():
    """Without this filter the model would be trained on its own output: a
    feedback loop that looks healthy and drifts away from reality."""
    entities = ENTITIES_RESPONSE + [
        {"id": f"urn:ngsi-ld:CrowdFlowObserved:Barcelona_Crowd_1{PREDICTION_ENTITY_SUFFIX}",
         "type": "CrowdFlowObserved"},
    ]
    with patch.dict(os.environ, {**AETHER_ENV, "DEVICE_IDS": ""}), \
         patch("crowd_predictions.helpers.aether.requests.get", return_value=_response(entities)):
        discovered = resolve_device_ids()

    assert len(discovered) == 3
    assert not any(d.endswith(PREDICTION_ENTITY_SUFFIX) for d in discovered)


def test_autodiscovery_honours_a_custom_entity_type():
    with patch.dict(os.environ, {**AETHER_ENV, "DEVICE_IDS": "", "ENTITY_TYPE": "OtroTipo"}), \
         patch("crowd_predictions.helpers.aether.requests.get", return_value=_response(ENTITIES_RESPONSE)) as get:
        resolve_device_ids()

    assert get.call_args.kwargs["params"]["types"] == "OtroTipo"


def test_autodiscovery_walks_every_page_instead_of_stopping_at_the_first():
    """A real bug: without limit/offset Orion-LD answers its default page of 20 and
    the 21st sensor onwards was never discovered - no error, just a model trained on
    part of the deployment. A full page has to be followed by another request."""
    page_1 = [{"id": f"urn:ngsi-ld:CrowdFlowObserved:S{i}", "type": "CrowdFlowObserved"}
              for i in range(1000)]
    page_2 = [{"id": "urn:ngsi-ld:CrowdFlowObserved:S1000", "type": "CrowdFlowObserved"}]

    with patch.dict(os.environ, {**AETHER_ENV, "DEVICE_IDS": ""}), \
         patch("crowd_predictions.helpers.aether.requests.get",
               side_effect=[_response(page_1), _response(page_2)]) as get:
        discovered = resolve_device_ids()

    assert len(discovered) == 1001
    assert [c.kwargs["params"]["offset"] for c in get.call_args_list] == [0, 1000]


def test_autodiscovery_does_not_ask_for_one_page_more_than_it_needs():
    """A short page IS the last one. Asking again costs a round trip per run against
    a broker that already said everything it had."""
    with patch.dict(os.environ, {**AETHER_ENV, "DEVICE_IDS": ""}), \
         patch("crowd_predictions.helpers.aether.requests.get",
               return_value=_response(ENTITIES_RESPONSE)) as get:
        resolve_device_ids()

    assert get.call_count == 1


def test_autodiscovery_fails_loudly_instead_of_predicting_zero_entities():
    with patch.dict(os.environ, {**AETHER_ENV, "DEVICE_IDS": ""}), \
         patch("crowd_predictions.helpers.aether.requests.get", return_value=_response([])):
        with pytest.raises(NoHistoryError, match="No entity of type"):
            resolve_device_ids()


def test_autodiscovery_distinguishes_a_failed_query_from_an_empty_one():
    with patch.dict(os.environ, {**AETHER_ENV, "DEVICE_IDS": ""}), \
         patch("crowd_predictions.helpers.aether.requests.get", side_effect=Exception("boom")):
        with pytest.raises(NoHistoryError, match="Could not query the broker"):
            resolve_device_ids()


# --------------------------------------------------------------------------
# Autodiscovery of zones (CrowdFlowZone) - resolve_zone_ids() shares its query/
# pagination/_pred-exclusion machinery with resolve_device_ids() above (see
# _resolve_entity_ids() in aether_history.py), so only its OWN wiring is
# re-tested here, not the whole broker-interaction surface again.
# --------------------------------------------------------------------------

ZONE_ENTITIES_RESPONSE = [
    {"id": "urn:ngsi-ld:CrowdFlowZone:Z01", "type": "CrowdFlowZone"},
    {"id": "urn:ngsi-ld:CrowdFlowZone:Z02", "type": "CrowdFlowZone"},
]


def test_explicit_zone_ids_win_over_autodiscovery():
    with patch.dict(os.environ, {**AETHER_ENV, "ZONE_IDS": "Z01, Z02"}), \
         patch("crowd_predictions.helpers.aether.requests.get") as get:
        assert resolve_zone_ids() == ["Z01", "Z02"]
    get.assert_not_called()


def test_zone_autodiscovery_asks_the_broker_for_crowdflowzone_by_default():
    with patch.dict(os.environ, {**AETHER_ENV, "ZONE_IDS": ""}), \
         patch("crowd_predictions.helpers.aether.requests.get",
               return_value=_response(ZONE_ENTITIES_RESPONSE)) as get:
        discovered = resolve_zone_ids()

    assert discovered == ["urn:ngsi-ld:CrowdFlowZone:Z01", "urn:ngsi-ld:CrowdFlowZone:Z02"]
    assert get.call_args.kwargs["params"]["types"] == "CrowdFlowZone"


def test_zone_autodiscovery_excludes_our_own_prediction_entities():
    entities = ZONE_ENTITIES_RESPONSE + [
        {"id": f"urn:ngsi-ld:CrowdFlowZone:Z01{PREDICTION_ENTITY_SUFFIX}", "type": "CrowdFlowZone"},
    ]
    with patch.dict(os.environ, {**AETHER_ENV, "ZONE_IDS": ""}), \
         patch("crowd_predictions.helpers.aether.requests.get", return_value=_response(entities)):
        discovered = resolve_zone_ids()

    assert len(discovered) == 2
    assert not any(d.endswith(PREDICTION_ENTITY_SUFFIX) for d in discovered)


def test_zone_autodiscovery_honours_a_custom_entity_type():
    with patch.dict(os.environ, {**AETHER_ENV, "ZONE_IDS": "", "CROWD_FLOW_ZONE_ENTITY_TYPE": "OtroTipo"}), \
         patch("crowd_predictions.helpers.aether.requests.get",
               return_value=_response(ZONE_ENTITIES_RESPONSE)) as get:
        resolve_zone_ids()

    assert get.call_args.kwargs["params"]["types"] == "OtroTipo"


def test_zone_autodiscovery_fails_loudly_instead_of_predicting_zero_zones():
    with patch.dict(os.environ, {**AETHER_ENV, "ZONE_IDS": ""}), \
         patch("crowd_predictions.helpers.aether.requests.get", return_value=_response([])):
        with pytest.raises(NoHistoryError, match="No entity of type"):
            resolve_zone_ids()


# --------------------------------------------------------------------------
# The reading window
# --------------------------------------------------------------------------

def test_minimum_window_covers_the_rolling_warmup_plus_the_holdout():
    with patch.dict(os.environ, {"TRAINING_HOLDOUT_DAYS": "14"}):
        assert minimum_window_hours() == (28 + 14 + 7) * 24  # 49 days
    # A wider holdout widens the floor: otherwise there would be nothing left to
    # train on, with no error.
    with patch.dict(os.environ, {"TRAINING_HOLDOUT_DAYS": "30"}):
        assert minimum_window_hours() == (28 + 30 + 7) * 24


def test_a_short_incremental_window_is_raised_to_the_floor():
    """The 504 h (21 days) the reference prediction ETL uses would silently empty the
    training table here: parking has no 28-day rolling features."""
    with patch.dict(os.environ, {"INCREMENTAL_HOURS": "504", "TRAINING_HOLDOUT_DAYS": "14"}):
        assert incremental_window_hours() == minimum_window_hours()


def test_a_wide_enough_incremental_window_is_honoured():
    with patch.dict(os.environ, {"INCREMENTAL_HOURS": "5000", "TRAINING_HOLDOUT_DAYS": "14"}):
        assert incremental_window_hours() == 5000


def test_the_warm_start_window_is_not_the_cold_one():
    """The count is different: the 14-day holdout has no function in the warm start
    (nothing is re-tuned, so there is nothing to validate with it), and what is read
    is not what is trained on - the 28 days behind are lookback for the features."""
    with patch.dict(os.environ, {"TRAINING_HOLDOUT_DAYS": "14"}, clear=False):
        os.environ.pop("INCREMENTAL_TRAIN_DAYS", None)
        assert incremental_train_days() == 2
        assert incremental_training_window_hours() == (28 + 2) * 24  # 30 days
        assert incremental_training_window_hours() < minimum_window_hours()  # 49 days


def test_the_warm_start_window_widens_with_incremental_train_days():
    """The 28 days of lookback cannot be lowered (rolling_*_28d would come out NaN
    and the feature would drop out), but the rows CAN be widened - which is what you
    do if the CronJob has been down for days."""
    with patch.dict(os.environ, {"INCREMENTAL_TRAIN_DAYS": "5"}):
        assert incremental_training_window_hours() == (28 + 5) * 24


def test_an_explicit_window_wins_over_the_incremental_flag():
    now = datetime(2026, 8, 3, 12, 0)
    start, _end = history_window(incremental=True, now=now, window_hours=48)
    assert start == "2026-08-01T12:00:00.000Z"


def test_cold_start_window_reaches_a_year_back():
    now = datetime(2026, 8, 3, 12, 0)
    start, end = history_window(incremental=False, now=now)
    assert start == "2025-08-03T12:00:00.000Z"
    assert end == "2026-08-03T12:00:00.000Z"
    assert (now - datetime.strptime(start, "%Y-%m-%dT%H:%M:%S.000Z")).days == COLD_START_DAYS


def test_incremental_window_is_shorter_than_cold_start_but_over_six_weeks():
    now = datetime(2026, 8, 3, 12, 0)
    with patch.dict(os.environ, {"TRAINING_HOLDOUT_DAYS": "14"}, clear=False):
        os.environ.pop("INCREMENTAL_HOURS", None)
        inc_start, _ = history_window(incremental=True, now=now)
    full_start, _ = history_window(incremental=False, now=now)

    inc_days = (now - datetime.strptime(inc_start, "%Y-%m-%dT%H:%M:%S.000Z")).days
    assert 42 <= inc_days < COLD_START_DAYS
    assert inc_start > full_start


# --------------------------------------------------------------------------
# load_history_bins(): the entry point train.py / predict.py use
# --------------------------------------------------------------------------

def test_load_history_bins_reads_and_converts_in_one_call():
    with patch.dict(os.environ, {**AETHER_ENV,
                                  "DEVICE_IDS": "urn:ngsi-ld:CrowdFlowObserved:Barcelona_Crowd_1",
                                  "CROWD_MEASURE_ID": "peopleCountMediumInterval"}), \
         patch("crowd_predictions.helpers.aether.requests.post", return_value=_response(TIMESERIES_RESPONSE)):
        bins = load_history_bins(incremental=True)

    assert len(bins) == 3
    assert bins[0]["device_id"] == "urn:ngsi-ld:CrowdFlowObserved:Barcelona_Crowd_1"
    assert bins[0]["occupancy"] == 15


def test_load_history_bins_reports_no_data_instead_of_returning_an_empty_list():
    """Verified case in PRE: the same query with the wrong scope answers 200 with
    an empty time_series. Returning [] here would surface much later as "the model
    cannot predict anything"."""
    with patch.dict(os.environ, {**AETHER_ENV, "DEVICE_IDS": "dev1"}), \
         patch("crowd_predictions.helpers.aether.requests.post",
               return_value=_response(EMPTY_TIMESERIES_RESPONSE)):
        with pytest.raises(NoHistoryError, match="returned NO DATA"):
            load_history_bins(incremental=True)


def test_load_history_bins_refuses_to_run_without_configuration():
    with patch.dict(os.environ, {"AETHER_LINK_URL": "", "FIWARE_TENANT": "libelium",
                                  "FIWARE_SCOPE": "/", "DEVICE_IDS": "dev1"}):
        with pytest.raises(aether.AetherConfigError, match="AETHER_LINK_URL"):
            load_history_bins()


def test_load_history_bins_uses_the_configured_measure():
    with patch.dict(os.environ, {**AETHER_ENV, "DEVICE_IDS": "dev1",
                                  "CROWD_MEASURE_ID": "peopleCountLongInterval"}), \
         patch("crowd_predictions.helpers.aether.requests.post",
               return_value=_response(TIMESERIES_RESPONSE)) as post:
        # The fixture only carries peopleCountMediumInterval, so asking for
        # another measure has to end up as "no data", not as data of the wrong
        # measure.
        with pytest.raises(NoHistoryError):
            load_history_bins(incremental=True)

    assert post.call_args.kwargs["json"][0]["measure_ids"] == ["peopleCountLongInterval"]
