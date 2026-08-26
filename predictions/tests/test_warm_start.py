"""
The warm start guards, unit by unit. The end-to-end mode switching lives in
tests/test_train_modes.py.
"""

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import numpy as np
import xgboost as xgb

from crowd_predictions import events_registry
from crowd_predictions.config import settings
from crowd_predictions.helpers.warm_start import (blocking_column_change, calendar_changed,
                                 events_registry_changed, force_full_retrain,
                                 full_retrain_is_due, max_estimators, metric_got_worse,
                                 n_estimators_increment, n_trees, room_for_more_trees,
                                 warm_start_fit, weather_availability_changed)


def _model(n_estimators=30):
    X = np.random.default_rng(0).random((120, 4))
    y = np.arange(120) % 17
    model = xgb.XGBRegressor(objective="count:poisson", n_estimators=n_estimators, max_depth=2)
    model.fit(X, y)
    return model, X, y


def test_n_trees_reads_the_booster_not_the_n_estimators_attribute():
    """After a warm start, n_estimators only holds the NEW trees and after
    load_model() it comes back as None - the cap has to look at the booster."""
    model, _, _ = _model(n_estimators=30)
    assert n_trees(model) == 30


def test_warm_start_adds_exactly_the_increment_on_top_of_the_stored_booster():
    model, X, y = _model(n_estimators=30)
    warm = warm_start_fit(model, X[:40], y[:40], {"objective": "count:poisson", "max_depth": 2},
                           increment=7)
    assert n_trees(warm) == 37


def test_room_for_more_trees_is_the_cap_that_forces_a_full_retrain():
    """50 a day is ~18000 a year and nobody prunes them."""
    model, _, _ = _model(n_estimators=30)
    with patch.dict(os.environ, {"MAX_ESTIMATORS": "100", "N_ESTIMATORS_INCREMENT": "50"}):
        assert room_for_more_trees(model) is True
    with patch.dict(os.environ, {"MAX_ESTIMATORS": "60", "N_ESTIMATORS_INCREMENT": "50"}):
        assert room_for_more_trees(model) is False


def test_n_estimators_increment_is_configurable():
    with patch.dict(os.environ, {"N_ESTIMATORS_INCREMENT": "13"}):
        assert n_estimators_increment() == 13


def test_blocking_column_change_detects_a_different_feature_set():
    """The history now supports rolling_mean_28d, which the booster never saw."""
    stored = ["hour_sin", "lag_1d", "zone_A"]
    current = ["hour_sin", "lag_1d", "rolling_mean_28d", "zone_A"]
    assert "rolling_mean_28d" in blocking_column_change(stored, current)
    # And the other way round: the feature disappears from what the history supports.
    assert "rolling_mean_28d" in blocking_column_change(current, stored)


def test_blocking_column_change_detects_a_new_zone_but_tolerates_one_that_left():
    """A NEW zone has no one-hot column in the booster: reindexing would train it
    as "no zone" with no error at all. One that stops reporting is harmless (its
    column simply stays at 0)."""
    stored = ["hour_sin", "zone_A", "zone_B"]
    assert "zone_C" in blocking_column_change(stored, ["hour_sin", "zone_A", "zone_C"])
    assert blocking_column_change(stored, ["hour_sin", "zone_A"]) == ""


def test_blocking_column_change_is_empty_when_nothing_changed():
    columns = ["hour_sin", "lag_1d", "zone_A"]
    assert blocking_column_change(columns, columns) == ""


def test_metric_got_worse_applies_the_tolerance_and_ignores_an_unknown_baseline():
    with patch.dict(os.environ, {"INCREMENTAL_MAE_TOLERANCE": "1.10"}):
        assert metric_got_worse(11.5, 10.0) is True    # +15%
        assert metric_got_worse(10.5, 10.0) is False   # +5%, inside the margin
        assert metric_got_worse(10.5, None) is False   # nothing to compare against


def test_force_full_retrain_reads_the_environment():
    with patch.dict(os.environ, {"FORCE_FULL_RETRAIN": "true"}):
        assert force_full_retrain() is True
    with patch.dict(os.environ, {"FORCE_FULL_RETRAIN": "false"}):
        assert force_full_retrain() is False


# --- Full retrain by AGE, so the increments do not pile up for ever ---

def _metrics_with_full_trained_at(days_ago):
    stamp = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return {"params": {"max_depth": 2}, "full_trained_at": stamp.isoformat()}


def test_a_recent_full_retrain_lets_the_increment_go_ahead():
    assert full_retrain_is_due(_metrics_with_full_trained_at(days_ago=5)) == ""


def test_an_old_full_retrain_forces_a_full_one():
    reason = full_retrain_is_due(_metrics_with_full_trained_at(days_ago=31))
    assert "31 days ago" in reason and "FULL_RETRAIN_AFTER_DAYS" in reason


def test_the_boundary_is_inclusive():
    assert full_retrain_is_due(_metrics_with_full_trained_at(days_ago=30)) != ""
    assert full_retrain_is_due(_metrics_with_full_trained_at(days_ago=29)) == ""


def test_a_bundle_with_no_stamp_is_treated_as_due():
    """Bundles written before this existed. One extra full retrain is cheaper than
    never doing another one."""
    assert full_retrain_is_due({"params": {}}) != ""


def test_an_unreadable_stamp_is_treated_as_due_instead_of_crashing():
    assert "unreadable" in full_retrain_is_due({"full_trained_at": "last tuesday"})


def test_a_naive_stamp_is_assumed_utc_and_does_not_crash():
    """isoformat() without tz - subtracting an aware from a naive datetime raises."""
    naive = (datetime.now(timezone.utc) - timedelta(days=40)).replace(tzinfo=None)
    assert "40 days ago" in full_retrain_is_due({"full_trained_at": naive.isoformat()})


def test_zero_disables_the_age_rule():
    """Escape hatch: only the tree cap decides."""
    with patch.dict(os.environ, {"FULL_RETRAIN_AFTER_DAYS": "0"}):
        assert full_retrain_is_due(_metrics_with_full_trained_at(days_ago=365)) == ""


def test_the_cap_now_sits_above_the_age_rule():
    """If the cap fired first the schedule would never be reached, so the cap has to
    be above increments x days.

    Constant against constant, NOT max_estimators() against a literal: settings read
    os.environ, and load_dotenv() finds the developer's .env from the module's own
    directory, so anything going through the accessors asserts the .env and not the
    code. Measured: DEFAULT_MAX_ESTIMATORS could be changed to 100 and the whole
    suite still passed locally."""
    assert (settings.DEFAULT_MAX_ESTIMATORS >
            settings.DEFAULT_FULL_RETRAIN_AFTER_DAYS * settings.DEFAULT_N_ESTIMATORS_INCREMENT)


# --- A timezone change redefines the calendar features without renaming a column ---

def test_the_same_timezone_lets_the_increment_go_ahead():
    with patch.dict(os.environ, {"CALENDAR_TIMEZONE": "Europe/Madrid"}):
        assert calendar_changed({"calendar_timezone": "Europe/Madrid"}) == ""


def test_a_changed_timezone_forces_a_full_retrain():
    """blocking_column_change() CANNOT see this: `hour` and `weekday` keep their
    names and just start meaning something else."""
    with patch.dict(os.environ, {"CALENDAR_TIMEZONE": "UTC"}):
        reason = calendar_changed({"calendar_timezone": "Europe/Madrid"})
    assert "CALENDAR_TIMEZONE changed" in reason and "Europe/Madrid -> UTC" in reason


def test_a_bundle_from_before_this_was_recorded_is_left_alone():
    """Unlike the age rule, this one does NOT force a retrain on an old bundle: there
    is no value to compare, and guessing would retrain everyone once for nothing."""
    assert calendar_changed({"params": {}}) == ""


# --- Weather flipping from a constant 0.0 to real values is the same class of
# silent drift as a timezone change - just for a different feature ---

def test_weather_still_unavailable_lets_the_increment_go_ahead():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("WEATHER_LAT", None)
        os.environ.pop("WEATHER_LON", None)
        os.environ.pop("WEATHER_TARGETS", None)
        assert weather_availability_changed({"weather_available": False}) == ""


def test_weather_becoming_available_forces_a_full_retrain():
    with patch.dict(os.environ, {"WEATHER_LAT": "43.54", "WEATHER_LON": "-5.66"}):
        reason = weather_availability_changed({"weather_available": False})
    assert "weather availability changed" in reason and "unavailable -> available" in reason


def test_a_weather_bundle_from_before_this_was_recorded_is_left_alone():
    assert weather_availability_changed({"params": {}}) == ""


# --- The events registry can change retroactively, on any day, without ever
# touching a column name - blocking_column_change cannot see it either ---

class _DictStorage:
    def __init__(self, files=None):
        self.files = files or {}

    def upload_file(self, filename, path):
        with open(path, "rb") as f:
            self.files[filename] = f.read()
        return path

    def download_file(self, filename, path):
        if filename not in self.files:
            raise FileNotFoundError(filename)
        with open(path, "wb") as f:
            f.write(self.files[filename])
        return path

    def delete_file(self, path):
        self.files.pop(path, None)
        return True

    def list_all(self):
        return sorted(self.files)


def _upload_registry_csv(storage, rows: str, tmp_path):
    with patch.dict(os.environ, {"FIWARE_TENANT": "t", "FIWARE_SCOPE": "/"}):
        local_path = str(tmp_path / "events_registry.csv")
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(rows)
        storage.upload_file(events_registry.events_registry_key(), local_path)


def test_an_unchanged_registry_lets_the_increment_go_ahead(tmp_path):
    storage = _DictStorage()
    rows = "date,event_type,device_ids,notes\n2026-04-09,large_event,,Concert\n"
    _upload_registry_csv(storage, rows, tmp_path)
    with patch.dict(os.environ, {"FIWARE_TENANT": "t", "FIWARE_SCOPE": "/"}):
        fp = events_registry.fingerprint(events_registry.load_events_registry(storage))
        assert events_registry_changed(storage, {"events_fingerprint": fp}) == ""


def test_a_new_event_forces_a_full_retrain_even_with_the_same_column_set(tmp_path):
    """The column IS event_magnitude either way - blocking_column_change sees no
    difference, which is exactly why this guard has to exist on its own."""
    storage = _DictStorage()
    rows = "date,event_type,device_ids,notes\n2026-04-09,large_event,,Concert\n"
    _upload_registry_csv(storage, rows, tmp_path)
    with patch.dict(os.environ, {"FIWARE_TENANT": "t", "FIWARE_SCOPE": "/"}):
        stale_fp = events_registry.fingerprint(events_registry.load_events_registry(storage))

    rows += "2026-09-02,small_event,SS3,Market\n"
    _upload_registry_csv(storage, rows, tmp_path)
    with patch.dict(os.environ, {"FIWARE_TENANT": "t", "FIWARE_SCOPE": "/"}):
        reason = events_registry_changed(storage, {"events_fingerprint": stale_fp})
    assert "events registry changed" in reason


def test_a_retroactive_edit_to_a_past_row_also_forces_a_full_retrain(tmp_path):
    """Not just new rows: editing a date already trained on rewrites
    event_magnitude on rows the stored trees learned as 0 - same danger, no new
    row needed."""
    storage = _DictStorage()
    rows = "date,event_type,device_ids,notes\n2026-04-09,small_event,,Concert\n"
    _upload_registry_csv(storage, rows, tmp_path)
    with patch.dict(os.environ, {"FIWARE_TENANT": "t", "FIWARE_SCOPE": "/"}):
        stale_fp = events_registry.fingerprint(events_registry.load_events_registry(storage))

    edited_rows = "date,event_type,device_ids,notes\n2026-04-09,large_event,,Concert (bigger than thought)\n"
    _upload_registry_csv(storage, edited_rows, tmp_path)
    with patch.dict(os.environ, {"FIWARE_TENANT": "t", "FIWARE_SCOPE": "/"}):
        reason = events_registry_changed(storage, {"events_fingerprint": stale_fp})
    assert "events registry changed" in reason


def test_reweighing_an_event_type_forces_the_retrain(tmp_path):
    """The registry file does not change and every row keeps its event_type, but
    every row's trained value did change - so the fingerprint hashes the magnitude,
    not the type, and the guard catches it without anyone remembering to."""
    storage = _DictStorage()
    rows = "date,event_type,device_ids,notes\n2026-04-09,large_event,,Concert\n"
    _upload_registry_csv(storage, rows, tmp_path)
    with patch.dict(os.environ, {"FIWARE_TENANT": "t", "FIWARE_SCOPE": "/"}):
        stale_fp = events_registry.fingerprint(events_registry.load_events_registry(storage))

        with patch.dict(os.environ, {"EVENT_MAGNITUDES": '{"large_event": 3}'}):
            reason = events_registry_changed(storage, {"events_fingerprint": stale_fp})

    assert "events registry changed" in reason


def test_an_events_bundle_from_before_this_was_recorded_is_left_alone():
    assert events_registry_changed(_DictStorage(), {"params": {}}) == ""
