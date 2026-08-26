"""
train.py end to end over a SYNTHETIC history: which features it uses depending on
how much history there is and cold vs warm start

Only the data source is stubbed (load_history_bins(), the live-platform read) and
the storage (a folder instead of S3): everything in between - features, selection,
floor, tuning, sidecars, warm start - is the real thing. Small hyperparameter grid
so the whole file runs in seconds.
"""

import json
import logging
import os
import shutil
from datetime import datetime, timedelta, timezone

from unittest.mock import patch

import pytest
import xgboost as xgb

import crowd_predictions.train_pipeline as train
from crowd_predictions.helpers.model_storage import COLUMNS_SUFFIX, METRICS_SUFFIX, model_storage_key
from crowd_predictions.helpers.warm_start import n_trees


class FolderStorage:
    """The StorageType contract over a local folder. download_file RAISES when the
    key is not there, which is how load_model_bundle tells cold from warm."""

    def __init__(self, root):
        self.root = root
        os.makedirs(root, exist_ok=True)

    def _path(self, key):
        return os.path.join(self.root, key.replace("/", "__"))

    def upload_file(self, filename, path):
        shutil.copy(path, self._path(filename))
        return path

    def download_file(self, filename, path):
        source = self._path(filename)
        if not os.path.exists(source):
            raise FileNotFoundError(filename)
        shutil.copy(source, path)
        return path

    def delete_file(self, path):
        os.remove(self._path(path))
        return True

    def list_all(self):
        return sorted(os.listdir(self.root))

    def has(self, filename):
        return os.path.exists(self._path(filename))


def _bins(n_days, zones=("A", "B"), start=datetime(2026, 1, 1)):
    """Hourly bins with a weekday/hour pattern - something real to learn, not noise."""
    return [
        {"zone_id": zone,
         "timestamp": start + timedelta(days=day, hours=hour),
         "occupancy": (100 if zone == "A" else 50)
                       + hour * 2
                       - (30 if (start + timedelta(days=day)).weekday() >= 5 else 0)}
        for zone in zones for day in range(n_days) for hour in range(24)
    ]


_COLD_60_DAYS = {}
"""The bundle of a 60-day cold start, trained once for the whole file. See env.cold_start."""

_COLD_60_DAYS_ENV = {}
COLD_BUNDLE_ENV = ("MAX_ESTIMATORS", "CALENDAR_TIMEZONE", "BACKTEST_HORIZON_HOURS",
                    "MODEL_OUTPUT_PATH")
"""What the cached bundle depends on, checked on reuse. See env.cold_start."""


@pytest.fixture
def env(tmp_path, monkeypatch):
    """train.py wired to a folder storage and to a stubbed data source, with a tiny
    tuning grid. `env.days` decides how much history the source returns."""
    storage = FolderStorage(str(tmp_path / "storage"))
    monkeypatch.setattr(train, "get_storage", lambda: storage)
    # Through the environment, not by patching a module constant: train.py reads
    # config/settings.py on every call, which is what makes the per-target isolation
    # work.
    monkeypatch.setenv("MODEL_OUTPUT_PATH", "test_model.json")
    monkeypatch.setenv("FIWARE_TENANT", "test_tenant")
    monkeypatch.setenv("FIWARE_SCOPE", "/")
    monkeypatch.delenv("FORCE_FULL_RETRAIN", raising=False)
    monkeypatch.delenv("MAX_ESTIMATORS", raising=False)
    monkeypatch.setenv("N_ESTIMATORS_INCREMENT", "50")
    # OFF by default here, like the tiny tuning grid: a 24-step recursive backtest per
    # cold start took this file from 22 s to 192 s. One test below turns it on.
    monkeypatch.setenv("BACKTEST_HORIZON_HOURS", "0")
    # OFF: the synthetic bins are anchored to a fixed date (2026-01-01), not to
    # wall-clock, so "freshest bin" drifts further from "now" as real time passes -
    # with the check on, every test in this file would eventually start going RED
    # for a reason that has nothing to do with what it is testing.
    monkeypatch.setenv("MAX_DATA_STALENESS_DAYS", "0")

    state = {"days": 60}

    def stub_load_history_bins(**kwargs):
        """Fakes the real load_history_bins()'s windowing (there it narrows the
        query's date range instead) - a warm start's window_hours must come back
        NARROWER than the cold start's full history, or
        test_the_warm_start_window_is_shorter_than_the_cold_one has nothing to
        measure."""
        bins = _bins(state["days"])
        window_hours = kwargs.get("window_hours")
        if window_hours and bins:
            cutoff = max(b["timestamp"] for b in bins) - timedelta(hours=window_hours)
            bins = [b for b in bins if b["timestamp"] >= cutoff]
        return bins

    # resolve_zone_ids() also stubbed: load_training_table() evaluates it to build
    # the device_ids= argument BEFORE load_history_bins() (also stubbed above) ever
    # runs, so leaving it real would still try to reach the broker.
    monkeypatch.setattr(train, "resolve_zone_ids", lambda: ["A", "B"])
    monkeypatch.setattr(train, "load_history_bins", stub_load_history_bins)

    real_tuning = train.tune_hyperparameters
    monkeypatch.setattr(train, "tune_hyperparameters",
                        lambda df, **kw: real_tuning(
                            df, param_grid={"max_depth": [2], "n_estimators": [20],
                                             "learning_rate": [0.1]}, **kw))

    class Env:
        pass

    e = Env()
    e.storage = storage
    e.state = state
    e.model_file = "test_model.json"
    e.tmp_path = tmp_path

    def run():
        return train.train_one_target("test_tenant", "/")

    def bundle():
        model = xgb.XGBRegressor()
        model.load_model(storage._path(model_storage_key(e.model_file)))
        with open(storage._path(model_storage_key(e.model_file + COLUMNS_SUFFIX))) as f:
            columns = json.load(f)
        with open(storage._path(model_storage_key(e.model_file + METRICS_SUFFIX))) as f:
            metrics = json.load(f)
        return model, columns, metrics

    def cold_start():
        """Leaves a 60-day cold start in storage and returns its bundle.

        For the many tests whose subject is the SECOND run: the first one was
        identical in all of them and cost ~1.1 s apiece. It is trained on the first
        call and copied in afterwards, so each test still mutates its own files.

        Call it BEFORE touching the environment, which is what every caller does
        anyway. The check is there because a shared cache fails far from its cause: a
        bundle trained under one test's overrides would be handed to all the others,
        and with random ordering the failure lands somewhere else."""
        state["days"] = 60
        env_now = {k: os.environ.get(k) for k in COLD_BUNDLE_ENV}

        if not _COLD_60_DAYS:
            assert run() == 0
            for suffix in ("", COLUMNS_SUFFIX, METRICS_SUFFIX):
                with open(storage._path(model_storage_key(e.model_file + suffix)), "rb") as f:
                    _COLD_60_DAYS[suffix] = f.read()
            _COLD_60_DAYS_ENV.update(env_now)
            return bundle()

        assert env_now == _COLD_60_DAYS_ENV, "cached under another environment; train it here"

        for suffix, blob in _COLD_60_DAYS.items():
            with open(storage._path(model_storage_key(e.model_file + suffix)), "wb") as f:
                f.write(blob)
        return bundle()

    e.run = run
    e.bundle = bundle
    e.cold_start = cold_start
    return e


def test_five_days_of_history_does_not_train_and_publishes_nothing(env, caplog):
    """Decided explicitly: below the 7-day floor NOTHING is published, not even the
    weekday baseline as a fallback - an entity that is sometimes a model and
    sometimes an average leaves the consumer unable to tell which one they read. The
    target goes RED for coherence with run_for_each_target."""
    env.state["days"] = 5
    with caplog.at_level(logging.INFO):
        exit_code = env.run()

    assert exit_code == 1
    assert not env.storage.has(model_storage_key(env.model_file))
    assert "NOT TRAINING and NOT PUBLISHING" in caplog.text
    assert "7-day tier" in caplog.text


def test_fifteen_days_trains_without_the_28_day_features_and_says_so(env, caplog):
    env.state["days"] = 15
    with caplog.at_level(logging.INFO):
        exit_code = env.run()

    assert exit_code == 0
    _model, columns, metrics = env.bundle()
    assert "rolling_mean_28d" not in columns and "rolling_std_28d" not in columns
    assert "lag_1w" in columns and "rolling_mean_7d" in columns
    assert metrics["mode"] == "full"
    # Logged on purpose: the day the 28-day features come in, the MAE changes
    # meaning, and without this line it looks like an unexplained jump.
    assert "FEATURES IN USE (15/17)" in caplog.text
    assert "left out: ['rolling_mean_28d', 'rolling_std_28d']" in caplog.text


def test_sixty_days_trains_with_all_seventeen_features(env, caplog):
    env.state["days"] = 60
    with caplog.at_level(logging.INFO):
        exit_code = env.run()

    assert exit_code == 0
    _model, columns, _metrics = env.bundle()
    assert "rolling_mean_28d" in columns and "rolling_std_28d" in columns
    assert "FEATURES IN USE (17/17)" in caplog.text


def test_second_run_is_a_warm_start_that_adds_exactly_the_increment(env, caplog):
    """First run: no model in storage -> cold, with tuning. Second run (one more day
    of data, as a daily CronJob would see it): warm, +N_ESTIMATORS_INCREMENT trees
    over the same booster."""
    _model, _columns, cold_metrics = env.cold_start()

    env.state["days"] = 61  # a day goes by and the platform ingests 24 more bins
    with caplog.at_level(logging.INFO):
        assert env.run() == 0
    warm_model, _columns, warm_metrics = env.bundle()

    assert cold_metrics["mode"] == "full"
    assert warm_metrics["mode"] == "incremental"
    assert n_trees(warm_model) == cold_metrics["n_trees"] + 50
    assert warm_metrics["n_trees"] == n_trees(warm_model)
    assert "WARM start" in caplog.text
    # The metric does NOT come from the rows it just fitted (which is what parking
    # does): the last day is held out.
    assert warm_metrics["mae_holdout_days"] == 1


def test_warm_start_reuses_the_stored_hyperparameters(env):
    _model, _columns, cold_metrics = env.cold_start()

    env.state["days"] = 61
    assert env.run() == 0
    _model, _columns, warm_metrics = env.bundle()

    assert warm_metrics["params"] == cold_metrics["params"]


def test_a_change_in_the_feature_set_forces_a_full_retrain(env, caplog):
    """The easiest thing to miss: the model was trained with 15 days (no rolling_*_28d)
    and the history now allows them. New trees over other columns would be a different model."""
    env.state["days"] = 15
    assert env.run() == 0
    _model, columns_15, metrics_15 = env.bundle()
    assert "rolling_mean_28d" not in columns_15

    env.state["days"] = 60
    with caplog.at_level(logging.INFO):
        assert env.run() == 0
    model_60, columns_60, metrics_60 = env.bundle()

    assert "the feature set changed" in caplog.text
    assert metrics_60["mode"] == "full"          # NOT incremental
    assert "rolling_mean_28d" in columns_60
    assert n_trees(model_60) != metrics_15["n_trees"] + 50


def test_a_bundle_from_before_event_magnitude_and_precip_mm_existed_forces_a_full_retrain(env, caplog):
    """Migration scenario: a bundle saved by OLD code (15 columns, no
    event_magnitude/precip_mm - they did not exist yet) meeting CURRENT code
    (always 17). blocking_column_change has to catch this by itself: this
    bundle predates weather_available/events_fingerprint too, so neither of
    those sidecar guards has anything to compare against (see
    test_a_weather_bundle_from_before_this_was_recorded_is_left_alone /
    the events equivalent, test_warm_start.py)."""
    _model, columns_17, _metrics = env.cold_start()
    assert "event_magnitude" in columns_17 and "precip_mm" in columns_17  # sanity: they are there

    # Rewrite the stored sidecar as if trained by code that never had them.
    old_columns = [c for c in columns_17 if c not in ("event_magnitude", "precip_mm")]
    columns_path = env.storage._path(model_storage_key(env.model_file + COLUMNS_SUFFIX))
    with open(columns_path, "w") as f:
        json.dump(old_columns, f)

    env.state["days"] = 61
    with caplog.at_level(logging.INFO):
        assert env.run() == 0
    _model, columns_after, metrics_after = env.bundle()

    assert "the feature set changed" in caplog.text
    assert metrics_after["mode"] == "full"
    assert set(columns_after) == set(columns_17)


def test_a_new_zone_forces_a_full_retrain(env, caplog):
    """A new zone has no one-hot column in the booster: reindexing would train it
    as "no zone" and nothing would complain."""
    env.cold_start()

    env.state["days"] = 61
    train.load_history_bins = lambda **kwargs: _bins(61, zones=("A", "B", "C"))
    with caplog.at_level(logging.INFO):
        assert env.run() == 0
    _model, columns, metrics = env.bundle()

    assert "new zones" in caplog.text
    assert metrics["mode"] == "full"
    assert "zone_C" in columns


def test_the_tree_cap_forces_a_full_retrain(env, caplog, monkeypatch):
    _model, _columns, cold_metrics = env.cold_start()

    monkeypatch.setenv("MAX_ESTIMATORS", str(cold_metrics["n_trees"]))
    env.state["days"] = 61
    with caplog.at_level(logging.INFO):
        assert env.run() == 0

    assert "MAX_ESTIMATORS" in caplog.text
    assert env.bundle()[2]["mode"] == "full"


def test_force_full_retrain_ignores_the_stored_model(env, caplog, monkeypatch):
    env.cold_start()

    monkeypatch.setenv("FORCE_FULL_RETRAIN", "true")
    env.state["days"] = 61
    with caplog.at_level(logging.INFO):
        assert env.run() == 0

    assert "FORCE_FULL_RETRAIN=true" in caplog.text
    assert env.bundle()[2]["mode"] == "full"


def test_no_new_data_leaves_the_model_untouched(env, caplog):
    """Ingestion stalled: with no new rows, adding 50 trees over the same ones only
    overfits them. It is not an error either - the model that is there is still
    valid."""
    _model, _columns, first_metrics = env.cold_start()

    with caplog.at_level(logging.INFO):
        assert env.run() == 0  # same data, same day
    _model, _columns, second_metrics = env.bundle()

    assert "NO NEW DATA" in caplog.text
    assert second_metrics["trained_at"] == first_metrics["trained_at"]  # not republished
    assert second_metrics["n_trees"] == first_metrics["n_trees"]


def test_a_worse_metric_discards_the_increment_and_retrains_in_full(env, caplog, monkeypatch):
    """Watchdog that parking does not have: the same held-out day is measured before
    and after the increment. With a tolerance of 0 any increment counts as worse,
    which is the cheapest way to exercise the branch."""
    env.cold_start()

    monkeypatch.setenv("INCREMENTAL_MAE_TOLERANCE", "0.0")
    env.state["days"] = 61
    with caplog.at_level(logging.INFO):
        assert env.run() == 0

    assert "MAE WORSENED with the increment" in caplog.text
    assert env.bundle()[2]["mode"] == "full"


def test_a_model_without_metrics_sidecar_is_retrained_in_full(env, caplog):
    """A model uploaded with a half-written bundle cannot be
    warm-started: no hyperparameters for the new trees and no MAE to compare
    against."""
    env.cold_start()
    os.remove(env.storage._path(model_storage_key(env.model_file + METRICS_SUFFIX)))

    env.state["days"] = 61
    with caplog.at_level(logging.INFO):
        assert env.run() == 0

    assert env.bundle()[2]["mode"] == "full"


def test_the_warm_start_window_is_shorter_than_the_cold_one(env, caplog):
    """The incremental count is NOT the cold one: 28 days of lookback for the
    features plus the new rows, with no 14-day holdout (nothing is re-tuned, so there
    is nothing to validate with it)."""
    env.cold_start()

    env.state["days"] = 61
    with caplog.at_level(logging.INFO):
        assert env.run() == 0

    # 30 days read (+ the bin on the boundary) instead of the 365 of the cold start,
    # and 10 usable days: the other 21 are lookback for the features.
    line = [l for l in caplog.text.splitlines() if "history read:" in l][-1]
    assert "history read: 31 days" in line
    assert "usable: 10 days" in line


# --- The full retrain by age, end to end ---

def test_the_warm_start_propagates_the_full_retrain_date_instead_of_restamping_it(env):
    """The whole age rule rests on this. `trained_at` moves on every save, so if the
    warm start re-stamped `full_trained_at` too, the model would never look old and a
    full retrain would never be due."""
    _model, _columns, cold = env.cold_start()

    env.state["days"] = 61
    assert env.run() == 0
    _model, _columns, warm = env.bundle()

    assert warm["mode"] == "incremental"
    assert warm["full_trained_at"] == cold["full_trained_at"], "re-stamped: the age rule is dead"
    assert warm["trained_at"] != cold["trained_at"], "trained_at must move on every save"


def test_an_old_bundle_is_fully_retrained_even_with_room_for_more_trees(env, caplog):
    """The tree cap is not reached (60 trees out of 2000) - it is the AGE that fires."""
    env.cold_start()

    # Age the stored bundle by 40 days, leaving everything else untouched.
    key = model_storage_key(env.model_file + METRICS_SUFFIX)
    path = env.storage._path(key)
    with open(path) as f:
        metrics = json.load(f)
    aged = datetime.now(timezone.utc) - timedelta(days=40)
    metrics["full_trained_at"] = aged.isoformat()
    with open(path, "w") as f:
        json.dump(metrics, f)

    env.state["days"] = 61
    with caplog.at_level(logging.WARNING):
        assert env.run() == 0

    assert "Full retrain DUE" in caplog.text
    assert "40 days ago" in caplog.text
    _model, _columns, after = env.bundle()
    assert after["mode"] == "full"
    # And the stamp is refreshed, so the next 30 days go back to warm starts.
    assert after["full_trained_at"] > metrics["full_trained_at"]


def test_changing_the_timezone_forces_a_full_retrain(env, caplog):
    """End to end. The columns are identical before and after, so the only thing that
    can catch it is the timezone recorded in the sidecar."""
    _model, columns_before, before = env.cold_start()
    assert before["calendar_timezone"] == "Europe/Madrid"

    env.state["days"] = 61
    with patch.dict(os.environ, {"CALENDAR_TIMEZONE": "UTC"}):
        with caplog.at_level(logging.WARNING):
            assert env.run() == 0
    _model, columns_after, after = env.bundle()

    assert "CALENDAR_TIMEZONE changed" in caplog.text
    assert after["mode"] == "full", "a warm start would mix two meanings of `hour`"
    assert after["calendar_timezone"] == "UTC"
    # The proof that no other guard could have caught it:
    assert columns_before == columns_after


def test_weather_becoming_available_forces_a_full_retrain(env, caplog):
    """End to end. precip_mm is still a column either way (it always is, see
    FEATURE_COLUMNS) - only weather_available in the sidecar can catch the
    switch from a constant 0.0 to real values."""
    _model, columns_before, before = env.cold_start()
    assert before["weather_available"] is False

    env.state["days"] = 61
    with patch.dict(os.environ, {"WEATHER_LAT": "43.54", "WEATHER_LON": "-5.66"}):
        with caplog.at_level(logging.WARNING):
            assert env.run() == 0
    _model, columns_after, after = env.bundle()

    assert "weather availability changed" in caplog.text
    assert after["mode"] == "full", "a warm start would mix constant-0.0 and real precip_mm"
    assert after["weather_available"] is True
    assert columns_before == columns_after


def test_a_new_event_forces_a_full_retrain(env, caplog):
    """End to end. event_magnitude is a column either way - only the fingerprint
    in the sidecar can catch that its VALUES changed for rows already trained."""
    from crowd_predictions import events_registry

    _model, columns_before, before = env.cold_start()
    assert "events_fingerprint" in before

    env.state["days"] = 61
    with patch.dict(os.environ, {"FIWARE_TENANT": "test_tenant", "FIWARE_SCOPE": "/"}):
        events_registry.append_event(env.storage, "2026-02-15", "large_event", notes="Fair")
    with caplog.at_level(logging.WARNING):
        assert env.run() == 0
    _model, columns_after, after = env.bundle()

    assert "events registry changed" in caplog.text
    assert after["mode"] == "full"
    assert after["events_fingerprint"] != before["events_fingerprint"]
    assert columns_before == columns_after


def test_the_horizon_backtest_measures_the_error_of_the_recursive_steps(env):
    """evaluate_model() measures ONE step over real lag/rolling. What gets published is
    recursive, each step fed its own output, and that error was measured nowhere - so
    `horizonStep` travelled to the consumer with no number behind it."""
    env.state["days"] = 60
    with patch.dict(os.environ, {"BACKTEST_HORIZON_HOURS": "4"}):
        assert env.run() == 0
    _model, _columns, metrics = env.bundle()

    by_step = metrics["mae_by_horizon_step"]
    # STRING keys on purpose: this comes back from JSON, where object keys always are.
    # Asserted here so nobody "tidies" them into ints and breaks the round trip.
    assert ["1", "2", "3", "4"] == sorted(k for k in by_step if k != "overall")
    assert all(isinstance(v, (int, float)) for v in by_step.values())
    # The point of measuring it: the one-step MAE is NOT the horizon MAE.
    assert by_step["overall"] != metrics["mae"] or by_step["1"] != by_step["4"]


def test_the_backtest_is_skippable(env):
    """It costs one feature-table rebuild per step; a deployment must be able to say no."""
    env.state["days"] = 60
    with patch.dict(os.environ, {"BACKTEST_HORIZON_HOURS": "0"}):
        assert env.run() == 0
    assert env.bundle()[2]["mae_by_horizon_step"] == {}
