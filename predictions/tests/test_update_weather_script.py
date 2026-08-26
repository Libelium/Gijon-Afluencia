"""
scripts/update_weather.py is now a manual multi-target backfill (the daily
refresh moved to daily_pipeline.py) - refresh_weather_one_target() itself
lives in crowd_predictions/weather.py (thin script, testable function), this
covers it running once per FIWARE_TARGETS entry via run_for_each_target.
"""

import os
from unittest.mock import patch

import pytest

from crowd_predictions import weather
from crowd_predictions.helpers.fiware_targets import run_for_each_target


@pytest.fixture
def one_target():
    with patch.dict(os.environ, {"FIWARE_TARGETS": "", "FIWARE_TENANT": "t", "FIWARE_SCOPE": "/"}):
        yield


def test_refreshes_every_target_not_just_the_one_in_the_environment():
    seen = []
    with patch.dict(os.environ, {"FIWARE_TARGETS": "a:/,b:/"}), \
         patch.object(weather, "update_weather_cache", lambda: seen.append("refreshed") or {"h1": {}}):
        exit_code = run_for_each_target(weather.refresh_weather_one_target, weather.logger)

    assert seen == ["refreshed", "refreshed"]
    assert exit_code == 0


def test_a_failing_target_does_not_stop_the_others(one_target, caplog):
    seen = []

    def flaky():
        seen.append(os.environ["FIWARE_TENANT"])
        if os.environ["FIWARE_TENANT"] == "bad":
            raise ConnectionError("Open-Meteo did not answer")
        return {}

    with patch.dict(os.environ, {"FIWARE_TARGETS": "bad:/,good:/"}), \
         patch.object(weather, "update_weather_cache", flaky):
        with caplog.at_level("ERROR"):
            exit_code = run_for_each_target(weather.refresh_weather_one_target, weather.logger)

    assert seen == ["bad", "good"]
    assert exit_code == 1


def test_refresh_weather_one_target_logs_the_hour_count(caplog):
    with patch.object(weather, "update_weather_cache", lambda: {"a": {}, "b": {}}):
        with caplog.at_level("INFO"):
            exit_code = weather.refresh_weather_one_target("t", "/")

    assert exit_code == 0
    assert "2 hours cached" in caplog.text
