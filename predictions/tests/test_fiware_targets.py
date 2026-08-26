import logging
import os
from unittest.mock import patch

import pytest

from crowd_predictions.helpers.fiware_targets import (fiware_target, parse_target_specs,
                                     run_for_each_target, target_label, target_slug)
from crowd_predictions.helpers.model_storage import model_storage_key


def _clean_env(**overrides):
    """patch.dict that also REMOVES FIWARE_* not being set: .env is loaded at
    import time by several modules, so they are present unless dropped."""
    env = dict(os.environ)
    for key in ("FIWARE_TARGETS", "FIWARE_TENANT", "FIWARE_SCOPE", "OTE_DEVICE_IDS"):
        env.pop(key, None)
    env.update(overrides)
    return patch.dict(os.environ, env, clear=True)


# --- device ids per target ---------------------------------------------------

def test_the_third_field_carries_the_devices_of_the_target():
    """The raw LIDAR feed has no tenant, only the device id of its URL: without saying
    which devices belong to whom, every target would publish every device's data."""
    with _clean_env(FIWARE_TARGETS="tenant_a:/:L1|L2,alicante:/:L3"):
        assert parse_target_specs() == [("tenant_a", "/", ("L1", "L2")),
                                        ("alicante", "/", ("L3",))]


def test_a_target_with_no_third_field_means_every_device():
    with _clean_env(FIWARE_TARGETS="tenant_a:/,alicante:/:L3"):
        assert parse_target_specs() == [("tenant_a", "/", None), ("alicante", "/", ("L3",))]


def test_an_empty_device_list_is_unset_not_no_devices():
    """A target with an empty list would publish nothing and still look healthy."""
    with _clean_env(FIWARE_TARGETS="tenant_a:/:"):
        assert parse_target_specs() == [("tenant_a", "/", None)]


def test_the_target_devices_reach_the_extract_through_the_environment():
    """fiware_target pins OTE_DEVICE_IDS, which the extract already reads, and restores
    it on exit so the next target does not inherit them."""
    with _clean_env(OTE_DEVICE_IDS="global"):
        with fiware_target("tenant_a", "/", ("L1", "L2")):
            assert os.environ["OTE_DEVICE_IDS"] == "L1,L2"
        assert os.environ["OTE_DEVICE_IDS"] == "global"

        # No devices for the target: whatever is set globally stays.
        with fiware_target("tenant_a", "/"):
            assert os.environ["OTE_DEVICE_IDS"] == "global"


# --- parse_target_specs -----------------------------------------------------------

def _pairs(raw: str = None) -> list:
    return [(tenant, scope) for tenant, scope, _devices in parse_target_specs(raw)]


def test_parses_several_targets_in_order():
    with _clean_env(FIWARE_TARGETS="demo_tenant:/,libelium:/,otra:zona"):
        assert _pairs() == [("demo_tenant", "/"), ("libelium", "/"), ("otra", "zona")]


def test_root_scope_can_be_left_implicit_either_way():
    """Both spellings have to normalize to the same pair, or the same deployment
    written two ways would get two different model keys."""
    for raw in ("libelium", "libelium:"):
        with _clean_env(FIWARE_TARGETS=raw):
            assert _pairs() == [("libelium", "/")]


def test_surrounding_whitespace_and_empty_items_are_ignored():
    with _clean_env(FIWARE_TARGETS="  demo_tenant : / , , libelium:/ ,"):
        assert _pairs() == [("demo_tenant", "/"), ("libelium", "/")]


def test_duplicates_are_dropped():
    """The same target twice would train it twice and the second upload would
    overwrite the first model - same key."""
    with _clean_env(FIWARE_TARGETS="libelium:/,libelium,libelium:/"):
        assert _pairs() == [("libelium", "/")]


def test_without_targets_it_falls_back_to_the_single_pair():
    """Retrocompatibility: an existing deployment has no FIWARE_TARGETS. Absent, blank,
    and with no scope are the same rule - a deployment upgrading hits all three."""
    with _clean_env(FIWARE_TENANT="demo_tenant", FIWARE_SCOPE="/"):
        assert _pairs() == [("demo_tenant", "/")]
    with _clean_env(FIWARE_TARGETS="   ", FIWARE_TENANT="demo_tenant", FIWARE_SCOPE="/"):
        assert _pairs() == [("demo_tenant", "/")]
    with _clean_env(FIWARE_TENANT="demo_tenant"):  # no FIWARE_SCOPE at all
        assert _pairs() == [("demo_tenant", "/")]


def test_explicit_raw_string_wins_over_the_environment():
    with _clean_env(FIWARE_TARGETS="from_env:/"):
        assert _pairs("from_arg:/") == [("from_arg", "/")]


# --- fiware_target -----------------------------------------------------------

def test_sets_the_pair_inside_the_block_and_restores_it_on_exit():
    with _clean_env(FIWARE_TENANT="a", FIWARE_SCOPE="/"):
        with fiware_target("b", "/zona"):
            assert os.environ["FIWARE_TENANT"] == "b"
            assert os.environ["FIWARE_SCOPE"] == "/zona"
        assert os.environ["FIWARE_TENANT"] == "a"
        assert os.environ["FIWARE_SCOPE"] == "/"


def test_restores_the_previous_pair_even_if_the_block_raises():
    with _clean_env(FIWARE_TENANT="a", FIWARE_SCOPE="/"):
        with pytest.raises(RuntimeError):
            with fiware_target("b", "/zona"):
                raise RuntimeError("boom")
        assert os.environ["FIWARE_TENANT"] == "a"
        assert os.environ["FIWARE_SCOPE"] == "/"


def test_unsets_variables_that_did_not_exist_before():
    """Leaving FIWARE_TENANT set behind would make the next reader think it is
    configured when it is not."""
    with _clean_env():
        with fiware_target("b", "/"):
            assert os.environ["FIWARE_TENANT"] == "b"
        assert "FIWARE_TENANT" not in os.environ
        assert "FIWARE_SCOPE" not in os.environ


def test_prefixes_the_logs_with_the_target_and_stops_on_exit(caplog):
    """With several targets, an "MAE=12.3" with no tenant does not say whose it is."""
    logger = logging.getLogger("test_fiware_targets.prefix")
    handler = logging.StreamHandler()
    logging.getLogger().addHandler(handler)
    try:
        with caplog.at_level(logging.INFO):
            with fiware_target("libelium", "/"):
                logger.info("MAE=12.3")
            logger.info("outside")
    finally:
        logging.getLogger().removeHandler(handler)

    messages = [record.getMessage() for record in caplog.records]
    assert "[libelium:/] MAE=12.3" in messages
    assert "outside" in messages


# --- segregation per target --------------------------------------------------

def test_two_targets_give_different_model_keys():
    """This checks the context manager really reaches it instead of assuming it."""
    keys = []
    with _clean_env(MODELS_PREFIX="prediction-models"):
        for tenant, scope in [("demo_tenant", "/"), ("libelium", "/")]:
            with fiware_target(tenant, scope):
                keys.append(model_storage_key("crowd_xgboost_model.json"))

    assert keys == ["prediction-models/demo_tenant/_/crowd_xgboost_model.json",
                    "prediction-models/libelium/_/crowd_xgboost_model.json"]
    assert keys[0] != keys[1]


def test_two_targets_give_different_prediction_output_dirs():
    """helpers/uploader.py publishes EVERY csv in the directory: sharing it would
    republish one tenant's predictions into the next one's."""
    from crowd_predictions.etl.predict.etl import PredictETL

    dirs = []
    with _clean_env(PREDICTIONS_FORECAST_OUTPUT_DIR="predictions_forecast"):
        for tenant, scope in [("demo_tenant", "/"), ("libelium", "/")]:
            with fiware_target(tenant, scope):
                dirs.append(PredictETL().output_dir)

    # "__": the root scope "/" normalizes to the single segment "_", same as in
    # the storage key.
    assert dirs == [os.path.join("predictions_forecast", "demo_tenant__"),
                    os.path.join("predictions_forecast", "libelium__")]


def test_the_uploaded_queue_message_carries_the_target_tenant():
    """The third consumer of the pair: the queue message (helpers/uploader.py)."""
    from crowd_predictions.helpers import uploader

    published = []
    with _clean_env(QUEUES_CONSUMER_API_URL="http://queues", QUEUES_CONSUMER_USER_ID="7"), \
            patch.object(uploader, "get_storage"), \
            patch.object(uploader.requests, "post",
                         side_effect=lambda url, json, timeout: published.append(json)
                         or type("R", (), {"status_code": 200, "text": ""})()), \
            patch.object(uploader.Path, "exists", return_value=True):
        for tenant in ("demo_tenant", "libelium"):
            with fiware_target(tenant, "/"):
                uploader.upload_csv_via_s3_and_queue("/tmp/x.csv", "urn:ngsi-ld:X:1_pred")

    assert [m["params"]["tenant"] for m in published] == ["demo_tenant", "libelium"]


def test_target_slug_and_label_read_the_active_target():
    with _clean_env(FIWARE_TENANT="t", FIWARE_SCOPE="/a/b"):
        assert target_slug() == "t_a_b"
    assert target_label("libelium", "/") == "[libelium:/]"


# --- run_for_each_target -----------------------------------------------------

def test_a_failing_target_does_not_abort_the_others():
    seen = []

    def run_one(tenant, scope):
        seen.append(tenant)
        if tenant == "malo":
            raise ValueError("no data")
        return 0

    with _clean_env(FIWARE_TARGETS="uno:/,malo:/,dos:/"):
        exit_code = run_for_each_target(run_one, logging.getLogger(__name__),
                                        config_errors=(ValueError,))

    assert seen == ["uno", "malo", "dos"]
    assert exit_code == 1


def test_a_non_zero_return_also_counts_as_a_failure():
    with _clean_env(FIWARE_TARGETS="uno:/,dos:/"):
        assert run_for_each_target(lambda t, s: 1 if t == "dos" else 0,
                                    logging.getLogger(__name__)) == 1


def test_an_unexpected_exception_is_isolated_too():
    seen = []

    def run_one(tenant, scope):
        seen.append(tenant)
        if tenant == "uno":
            raise KeyError("a bug here")
        return 0

    with _clean_env(FIWARE_TARGETS="uno:/,dos:/"):
        assert run_for_each_target(run_one, logging.getLogger(__name__),
                                    config_errors=(ValueError,)) == 1
    assert seen == ["uno", "dos"]


def test_exit_code_is_zero_when_every_target_succeeds():
    with _clean_env(FIWARE_TARGETS="uno:/,dos:/"):
        assert run_for_each_target(lambda t, s: 0, logging.getLogger(__name__)) == 0


def test_each_target_runs_with_its_own_pair_active():
    pairs = []
    with _clean_env(FIWARE_TARGETS="uno:/,dos:/zona"):
        run_for_each_target(
            lambda t, s: pairs.append((os.environ["FIWARE_TENANT"], os.environ["FIWARE_SCOPE"])) or 0,
            logging.getLogger(__name__))
    assert pairs == [("uno", "/"), ("dos", "/zona")]


def test_the_summary_says_how_many_targets_are_ok(caplog):
    with _clean_env(FIWARE_TARGETS="uno:/,malo:/,dos:/"), caplog.at_level(logging.INFO):
        run_for_each_target(lambda t, s: 1 if t == "malo" else 0,
                            logging.getLogger(__name__))
    assert any("SUMMARY: 2/3 targets OK" in r.getMessage() for r in caplog.records)
