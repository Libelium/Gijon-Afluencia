"""
Tests of config/settings.py.

The first block is the important one: it guards the property the whole multi-tenant
mechanism rests on. If somebody caches the settings, helpers/fiware_targets.py
stops isolating the targets and every one of them reads the first one's tenant,
without a single error anywhere.

⚠️ An assert on a DEFAULT has to go through `no_env()`. load_dotenv() finds the
developer's .env from the module's own directory, whatever the cwd, so anything
reading the accessors asserts that file and not the code. Measured: a default could
be changed to a wrong value and the whole suite still passed locally (it would only
fail in CI, where there is no .env).
"""

import json
import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from crowd_predictions.config import settings
from crowd_predictions.helpers.fiware_targets import fiware_target, parse_target_specs, target_slug
from crowd_predictions.helpers.model_storage import model_storage_key


def no_env(**overrides):
    """The environment WITHOUT the developer's .env, plus whatever the test sets."""
    return patch.dict(os.environ, overrides, clear=True)


# --- Nothing is cached: the same accessor must follow the environment ---

def test_the_tenant_is_read_on_every_call_and_not_cached():
    with patch.dict(os.environ, {"FIWARE_TENANT": "tenant_a"}):
        assert settings.fiware().FIWARE_TENANT == "tenant_a"
    with patch.dict(os.environ, {"FIWARE_TENANT": "tenant_b"}):
        assert settings.fiware().FIWARE_TENANT == "tenant_b"


def test_the_target_context_manager_still_isolates_the_model_key():
    """The end-to-end version of the test above: two targets in the same process
    must not share the storage key."""
    with patch.dict(os.environ, {"MODELS_PREFIX": "p", "FIWARE_TENANT": "", "FIWARE_SCOPE": "/"}):
        with fiware_target("tenant_a", "/"):
            key_a = model_storage_key("m.json")
        with fiware_target("tenant_b", "/"):
            key_b = model_storage_key("m.json")

    assert key_a == "p/tenant_a/_/m.json"
    assert key_b == "p/tenant_b/_/m.json"


def test_the_targets_list_follows_the_environment_too():
    with patch.dict(os.environ, {"FIWARE_TARGETS": "a:/,b:/"}):
        assert parse_target_specs() == [("a", "/", None), ("b", "/", None)]
    with patch.dict(os.environ, {"FIWARE_TARGETS": "c:/"}):
        assert parse_target_specs() == [("c", "/", None)]


def test_the_output_slug_follows_the_active_target():
    with patch.dict(os.environ, {"FIWARE_TENANT": "x", "FIWARE_SCOPE": "/"}):
        with fiware_target("tenant_a", "/"):
            assert target_slug() == "tenant_a__"
        with fiware_target("tenant_b", "/sub"):
            assert target_slug() == "tenant_b_sub"


# --- An empty variable means "not set", which is how .env.example ships ---

def test_an_empty_variable_falls_back_to_the_default():
    """`ROLLING_MIN_COVERAGE=` in .env means unset, not "". Without this the typed
    fields would fail validation on an empty string."""
    with patch.dict(os.environ, {"ROLLING_MIN_COVERAGE": "", "TRAINING_HOLDOUT_DAYS": ""}):
        training = settings.training()
    assert training.ROLLING_MIN_COVERAGE == settings.DEFAULT_ROLLING_MIN_COVERAGE
    assert training.TRAINING_HOLDOUT_DAYS == settings.DEFAULT_HOLDOUT_DAYS


def test_an_empty_optional_stays_none():
    """INCREMENTAL_HOURS has no numeric default on purpose: None means "use the
    floor computed by helpers/aether_history.minimum_window_hours()"."""
    with patch.dict(os.environ, {"INCREMENTAL_HOURS": ""}):
        assert settings.training().INCREMENTAL_HOURS is None


# --- Types are validated, instead of blowing up far from the cause ---

@pytest.mark.parametrize("variable,value", [
    ("TRAINING_HOLDOUT_DAYS", "fourteen"),
    ("INCREMENTAL_MAE_TOLERANCE", "1,10"),   # comma as the decimal separator
    ("MAX_ESTIMATORS", "1000.5"),
])
def test_a_non_numeric_value_fails_at_the_settings_and_not_deep_inside(variable, value):
    with patch.dict(os.environ, {variable: value}):
        with pytest.raises(ValidationError):
            settings.training()


def test_a_bool_accepts_the_usual_spellings():
    for value in ("true", "True", "1", "yes"):
        with patch.dict(os.environ, {"FORCE_FULL_RETRAIN": value}):
            assert settings.training().FORCE_FULL_RETRAIN is True
    for value in ("false", "False", "0", "no"):
        with patch.dict(os.environ, {"FORCE_FULL_RETRAIN": value}):
            assert settings.training().FORCE_FULL_RETRAIN is False


# --- Small behaviours that used to live scattered in the consumers ---

def test_the_aether_url_loses_its_trailing_slash():
    """Every caller concatenates onto it; "//api/v1/..." is not redirected."""
    with patch.dict(os.environ, {"AETHER_LINK_URL": "https://aether.example/"}):
        assert settings.aether().AETHER_LINK_URL == "https://aether.example"


def test_the_device_id_list_ignores_blanks():
    with patch.dict(os.environ, {"DEVICE_IDS": " a , ,b "}):
        assert settings.aether().device_id_list() == ["a", "b"]
    with patch.dict(os.environ, {"DEVICE_IDS": ""}):
        assert settings.aether().device_id_list() == []


def test_anomaly_config_parses_json_per_datamodel():
    config = {"CrowdFlowZone": {"measures": ["occupancy"], "cadence_minutes": 90},
             "CrowdFlowPrediction": {"measures": ["predictedOccupancy"], "cadence_minutes": 1440}}
    with patch.dict(os.environ, {"ANOMALY_CONFIG": json.dumps(config)}):
        anomaly = settings.anomaly()
        assert anomaly.measures_for("CrowdFlowZone") == ["occupancy"]
        assert anomaly.cadence_minutes_for("CrowdFlowZone") == 90
        assert anomaly.is_enabled_for("CrowdFlowZone") is True
        assert anomaly.is_enabled_for("CrowdFlowLidarZone") is False  # not in the config at all


def test_anomaly_config_empty_or_unset_disables_everything_without_crashing():
    """ANOMALY_CONFIG= (empty) is this file's own "not set" convention - it
    must not reach pydantic-settings' JSON auto-decoder, which raises on an
    empty string for a dict-typed field (confirmed against the installed
    pydantic-settings; that is exactly why ANOMALY_CONFIG is a plain str field
    with its own hand-rolled parser, not Dict[str, Any])."""
    with patch.dict(os.environ, {"ANOMALY_CONFIG": ""}):
        assert settings.anomaly().is_enabled_for("CrowdFlowZone") is False
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("ANOMALY_CONFIG", None)
        assert settings.anomaly().is_enabled_for("CrowdFlowZone") is False


def test_anomaly_config_malformed_json_is_ignored_not_raised():
    with patch.dict(os.environ, {"ANOMALY_CONFIG": "{not valid json"}):
        assert settings.anomaly().is_enabled_for("CrowdFlowZone") is False


def test_anomaly_config_fails_closed_without_cadence_minutes():
    """Measures configured but no cadence: every "how many points" knob is
    declared as a duration and converted through the cadence, so without it the
    datamodel is not configured yet - not configured with defaults."""
    config = {"CrowdFlowZone": {"measures": ["occupancy"]}}
    with patch.dict(os.environ, {"ANOMALY_CONFIG": json.dumps(config)}):
        assert settings.anomaly().is_enabled_for("CrowdFlowZone") is False


def test_an_unknown_field_is_ignored_instead_of_raising():
    """extra="ignore" has to be asserted by passing the extra as a KWARG. Through the
    environment it is unfalsifiable: pydantic-settings only feeds the variables that
    match a field name, so a stray env var never reaches the extras validator at all -
    the test passed with extra="forbid" too."""
    assert settings.TrainingSettings(SOMETHING_ELSE_ENTIRELY="x").MODEL_OUTPUT_PATH is not None


# --- What used to be hardcoded, now configurable ---

def test_the_queue_user_id_has_no_default():
    """It used to be a hardcoded 1, the admin account: the consumer notifies that
    user on EVERY published CSV. Guessing it floods a real person, so there is no
    default and the uploader refuses to publish without it."""
    with patch.dict(os.environ, {"QUEUES_CONSUMER_USER_ID": ""}):
        assert settings.queue().QUEUES_CONSUMER_USER_ID is None
    with patch.dict(os.environ, {"QUEUES_CONSUMER_USER_ID": "42"}):
        assert settings.queue().QUEUES_CONSUMER_USER_ID == 42


def test_the_holiday_region_is_configurable():
    """No region is inherited: absent subdivision means national holidays only, which
    loses precision but never marks the wrong days."""
    with no_env():
        calendar = settings.calendar()
    assert calendar.HOLIDAYS_SUBDIVISION is None
    # "none" and empty mean the same; the explicit word exists so a target can override
    # an inherited value - holidays.country_holidays("PT", subdiv="AS") raises.
    with patch.dict(os.environ, {"HOLIDAYS_COUNTRY": "PT", "HOLIDAYS_SUBDIVISION": "none"}):
        calendar = settings.calendar()
        assert calendar.HOLIDAYS_COUNTRY == "PT"
        assert calendar.HOLIDAYS_SUBDIVISION is None


def test_the_calendar_fails_instead_of_guessing_a_timezone_or_country():
    """Both would shift or mislabel EVERY calendar feature, and neither has a neutral
    value to fall back to."""
    with no_env():
        calendar = settings.calendar()
        for accessor in (calendar.timezone, calendar.country):
            try:
                accessor()
                assert False, "should have raised"
            except ValueError as e:
                assert "no fallback" in str(e)


def test_the_high_season_ranges_parse_including_the_one_crossing_the_year():
    with no_env():
        assert settings.calendar().high_season_ranges() == []
    with patch.dict(os.environ, {"HIGH_SEASON_RANGES": "06-15..09-15,12-20..01-06"}):
        assert settings.calendar().high_season_ranges() == [((6, 15), (9, 15)), ((12, 20), (1, 6))]
    with patch.dict(os.environ, {"HIGH_SEASON_RANGES": "01-07..03-31"}):
        assert settings.calendar().high_season_ranges() == [((1, 7), (3, 31))]


@pytest.mark.parametrize("value", ["06-15", "06-15..", "13-01..09-15", "06-32..09-15", "junio..sept"])
def test_a_malformed_high_season_range_fails_naming_the_variable(value):
    """It has to fail here, not silently mark the wrong days as high season."""
    with patch.dict(os.environ, {"HIGH_SEASON_RANGES": value}):
        with pytest.raises(ValueError, match="HIGH_SEASON_RANGES"):
            settings.calendar().high_season_ranges()


def test_the_published_entity_types_are_configurable():
    """CrowdFlowPrediction is PROVISIONAL until the real datamodel is confirmed, so
    renaming it must not need a code change."""
    with no_env():
        assert settings.fusion().CROWD_FLOW_ZONE_ENTITY_TYPE == "CrowdFlowZone"
        assert settings.prediction().PREDICTION_ENTITY_TYPE == "CrowdFlowPrediction"
    with patch.dict(os.environ, {"PREDICTION_ENTITY_TYPE": "CrowdFlowForecast"}):
        assert settings.prediction().PREDICTION_ENTITY_TYPE == "CrowdFlowForecast"


def test_the_ote_ingestion_defaults():
    """The gap decides permanence AND transits, and the entity types are provisional:
    both are the kind of number that must not live buried in a module."""
    with no_env():
        ote = settings.ote()
    assert ote.OTE_TRACK_GAP_SECONDS == 30
    assert ote.OTE_STATIONARY_MAX_DISPLACEMENT_M == 1.0
    assert ote.OTE_WINDOW_SECONDS == 3600
    assert ote.OTE_RAW_PREFIX == "ote/raw"
    assert ote.OTE_READ_MARGIN_SECONDS == 3600
    # The vendor's whole taxonomy, so `vehicleCount` comes out of the same mechanism as
    # `adultCount`: there is no separate path counting vehicles. Vehicle first: it also
    # doubles as resolve_label()'s priority order, and vehicle outranks adult.
    assert ote.label_attrs() == ["vehicle", "adult"]
    assert (ote.OTE_ZONE_ENTITY_TYPE, ote.OTE_OBSERVED_ENTITY_TYPE,
            ote.OTE_DEVICE_ENTITY_TYPE) == ("CrowdFlowLidarZone", "CrowdFlowLidarObserved",
                                            "CrowdFlowLidarDevice")


def test_the_ote_label_list_ignores_blanks():
    with patch.dict(os.environ, {"OTE_LABEL_ATTRS": "adult, child ,"}):
        assert settings.ote().label_attrs() == ["adult", "child"]


def test_nothing_is_published_without_the_queue_user_id(tmp_path):
    """The guard, end to end: it must refuse rather than guess an id whose owner then
    gets a notification per CSV.

    The CSV has to EXIST. With a made-up path the function returns False at
    `csv_path.exists()` long before reaching the guard, and the test passes even with
    the guard deleted - which is exactly what it did until a mutation run caught it."""
    from unittest.mock import MagicMock, patch as mpatch
    from crowd_predictions.helpers import uploader

    csv = tmp_path / "urn:ngsi-ld:X:1.csv"
    csv.write_text("urn,type,timestamp\nurn:ngsi-ld:X:1,X,2026-01-01\n")

    with patch.dict(os.environ, {"QUEUES_CONSUMER_API_URL": "https://queues.local",
                                 "QUEUES_CONSUMER_USER_ID": "",
                                 "FIWARE_TENANT": "t", "FIWARE_SCOPE": "/"}), \
            mpatch.object(uploader, "get_storage", return_value=MagicMock()), \
            mpatch.object(uploader.requests, "post") as post:
        assert uploader.upload_csv_via_s3_and_queue(str(csv), "urn:ngsi-ld:X:1") is False

    post.assert_not_called()


def test_nothing_is_published_with_an_empty_tenant(tmp_path):
    """Same shape, the other guard: the queue would accept the job and the platform would
    create no entity, so the run would look successful."""
    from unittest.mock import MagicMock, patch as mpatch
    from crowd_predictions.helpers import uploader

    csv = tmp_path / "urn:ngsi-ld:X:1.csv"
    csv.write_text("urn,type,timestamp\nurn:ngsi-ld:X:1,X,2026-01-01\n")

    with patch.dict(os.environ, {"QUEUES_CONSUMER_API_URL": "https://queues.local",
                                 "QUEUES_CONSUMER_USER_ID": "7",
                                 "FIWARE_TENANT": "", "FIWARE_SCOPE": "/"}), \
            mpatch.object(uploader, "get_storage", return_value=MagicMock()), \
            mpatch.object(uploader.requests, "post") as post:
        assert uploader.upload_csv_via_s3_and_queue(str(csv), "urn:ngsi-ld:X:1") is False

    post.assert_not_called()
