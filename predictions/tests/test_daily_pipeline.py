"""
The daily cycle: train + predict in one run.

The property under test is the one that makes this module worth existing, and the
one the reference prediction ETL does not have: a training failure must NOT stop the
prediction, because prediction reads the model from storage and yesterday's model
still publishes something useful. But the run must go RED, so nobody reads
"published" as "healthy".
"""

import os
from unittest.mock import patch

import pytest

from crowd_predictions import daily_pipeline
from crowd_predictions.helpers.aether import AetherConfigError


@pytest.fixture
def one_target():
    """A single target, so run_for_each_target does exactly one pass."""
    with patch.dict(os.environ, {"FIWARE_TARGETS": "", "FIWARE_TENANT": "t", "FIWARE_SCOPE": "/"}):
        yield


def test_both_halves_run_in_order_and_the_run_is_green(one_target):
    calls = []
    with patch.object(daily_pipeline.weather, "update_weather_cache", lambda: {}), \
            patch.object(daily_pipeline, "train_one_target", lambda t, s: calls.append("train") or 0), \
            patch.object(daily_pipeline, "predict_one_target", lambda t, s: calls.append("predict") or 0):
        assert daily_pipeline.main() == 0

    assert calls == ["train", "predict"]


def test_weather_is_refreshed_before_training(one_target):
    """First step of train_then_predict, per tenant/scope (see the docstring) - it
    must run BEFORE train_one_target, not after or in parallel."""
    calls = []
    with patch.object(daily_pipeline.weather, "update_weather_cache",
                      lambda: calls.append("weather") or {}), \
            patch.object(daily_pipeline, "train_one_target", lambda t, s: calls.append("train") or 0), \
            patch.object(daily_pipeline, "predict_one_target", lambda t, s: calls.append("predict") or 0):
        assert daily_pipeline.main() == 0

    assert calls == ["weather", "train", "predict"]


def test_a_weather_refresh_failure_still_trains_and_predicts(one_target, caplog):
    """Same tolerance as a training failure: Open-Meteo being down must not cost
    the day's training/prediction, only leave precip_mm on whatever was cached
    before (see weather.py)."""
    calls = []

    def boom():
        raise ConnectionError("Open-Meteo did not answer")

    with patch.object(daily_pipeline.weather, "update_weather_cache", boom), \
            patch.object(daily_pipeline, "train_one_target", lambda t, s: calls.append("train") or 0), \
            patch.object(daily_pipeline, "predict_one_target", lambda t, s: calls.append("predict") or 0):
        with caplog.at_level("ERROR"):
            exit_code = daily_pipeline.main()

    assert calls == ["train", "predict"]
    assert exit_code == 0, "a weather hiccup must not turn a healthy run red"
    assert "Weather cache refresh failed" in caplog.text


def test_a_successful_weather_refresh_clears_the_training_data_caches(one_target):
    """training_data._cached_weather_cache is per-process - without clearing it
    here, a refresh in a long-lived process would be invisible until restart."""
    with patch.object(daily_pipeline.weather, "update_weather_cache", lambda: {"h": {}}), \
            patch.object(daily_pipeline.training_data, "clear_caches") as mock_clear, \
            patch.object(daily_pipeline, "train_one_target", lambda t, s: 0), \
            patch.object(daily_pipeline, "predict_one_target", lambda t, s: 0):
        daily_pipeline.main()

    mock_clear.assert_called_once()


def test_a_failed_weather_refresh_does_not_clear_the_caches(one_target):
    """Nothing new was written - clearing here would just cost an extra
    round-trip on the very next add_calendar_features() call, for no reason."""
    def boom():
        raise ConnectionError("Open-Meteo did not answer")

    with patch.object(daily_pipeline.weather, "update_weather_cache", boom), \
            patch.object(daily_pipeline.training_data, "clear_caches") as mock_clear, \
            patch.object(daily_pipeline, "train_one_target", lambda t, s: 0), \
            patch.object(daily_pipeline, "predict_one_target", lambda t, s: 0):
        daily_pipeline.main()

    mock_clear.assert_not_called()


def test_a_training_failure_still_predicts_but_goes_red(one_target, caplog):
    """The core of it. Parking chains its stages with `and`, so this case publishes
    nothing at all."""
    calls = []
    with patch.object(daily_pipeline, "train_one_target", lambda t, s: calls.append("train") or 1), \
            patch.object(daily_pipeline, "predict_one_target", lambda t, s: calls.append("predict") or 0):
        with caplog.at_level("WARNING"):
            exit_code = daily_pipeline.main()

    assert calls == ["train", "predict"], "the prediction must run even if training failed"
    assert exit_code == 1, "and the run must not look healthy"
    assert "PREVIOUSLY stored" in caplog.text


def test_a_training_EXCEPTION_still_predicts(one_target, caplog):
    """Not just a non-zero code: an AetherConfigError raised while training would
    otherwise reach run_for_each_target, abort the target and skip the prediction."""
    calls = []

    def boom(tenant, scope):
        calls.append("train")
        raise AetherConfigError("AETHER_LINK_URL is not configured")

    with patch.object(daily_pipeline, "train_one_target", boom), \
            patch.object(daily_pipeline, "predict_one_target", lambda t, s: calls.append("predict") or 0):
        with caplog.at_level("ERROR"):
            exit_code = daily_pipeline.main()

    assert calls == ["train", "predict"]
    assert exit_code == 1
    assert "TRAINING FAILED" in caplog.text


def test_an_unexpected_training_error_is_also_survived(one_target):
    """Anything, not only the three config errors: the prediction is what the digital
    twin consumes, and it must not depend on the training half being bug-free."""
    calls = []

    def boom(tenant, scope):
        calls.append("train")
        raise KeyError("something nobody predicted")

    with patch.object(daily_pipeline, "train_one_target", boom), \
            patch.object(daily_pipeline, "predict_one_target", lambda t, s: calls.append("predict") or 0):
        assert daily_pipeline.main() == 1

    assert calls == ["train", "predict"]


def test_a_prediction_failure_is_red_too():
    with patch.dict(os.environ, {"FIWARE_TARGETS": "", "FIWARE_TENANT": "t", "FIWARE_SCOPE": "/"}):
        with patch.object(daily_pipeline, "train_one_target", lambda t, s: 0), \
                patch.object(daily_pipeline, "predict_one_target", lambda t, s: 1):
            assert daily_pipeline.main() == 1


def test_one_failing_target_does_not_stop_the_others():
    """Same criterion as the separate entry points: a tenant with no data must not
    leave the rest untrained."""
    seen = []

    def train(tenant, scope):
        seen.append(tenant)
        if tenant == "bad":
            raise AetherConfigError("no url")
        return 0

    with patch.dict(os.environ, {"FIWARE_TARGETS": "bad:/,good:/"}):
        with patch.object(daily_pipeline, "train_one_target", train), \
                patch.object(daily_pipeline, "predict_one_target", lambda t, s: 0):
            exit_code = daily_pipeline.main()

    assert seen == ["bad", "good"]
    assert exit_code == 1
