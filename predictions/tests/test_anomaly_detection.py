"""
anomaly_detection/ - the datamodel-agnostic vertical, unit by unit plus the
storage/config wiring of evaluate_batch().

Two things these tests deliberately do NOT cover:
  - the ingestion (there is no entry point yet: nothing reads entities off the
    platform, aligns their measures into co-temporal points and publishes the
    verdicts - when that exists it gets its own tests);
  - anything about zones or occupancy. Every fixture here uses a made-up
    datamodel with made-up measure names, which is the whole point: if a test
    needed to know what an aforo is, the vertical would have leaked.

FIXED_CALENDAR/`calendar: []` is used in the pure-algorithm tests to isolate them
from the calendar block, which has its own tests below.
"""

import json
import math
import os
import random
import statistics
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from crowd_predictions.anomaly_detection import storage as anomaly_storage
from crowd_predictions.anomaly_detection.core import (
    EXTREME_DIMENSION_MIN_CONSECUTIVE, MAX_SUBCLUSTERS, MIN_POINTS_FLOOR,
    DatamodelAnomalyState, DatamodelProfile, RunningStats, build_feature_vector,
    calendar_column_names, calendar_context, calendar_row, default_birch_threshold,
    derived_indices_for, evaluate_batch, evaluate_point, feature_columns_for,
    is_scorable, normalize_vector, score_outlier,
)

T0 = datetime(2026, 8, 12, 10, 0)
NO_CALENDAR = []


class _MemoryStorage:
    """The StorageType contract in memory: a successful download guarantees the
    local path now holds the content, and a missing key raises - a MagicMock would
    "succeed" without writing the file and hide exactly the bugs this catches."""

    def __init__(self):
        self.files = {}
        self.uploads = []

    def upload_file(self, key, path):
        with open(path, "rb") as f:
            self.files[key] = f.read()
        self.uploads.append(key)
        return path

    def download_file(self, key, path):
        if key not in self.files:
            raise FileNotFoundError(key)
        with open(path, "wb") as f:
            f.write(self.files[key])
        return path


class _FailingUploadStorage(_MemoryStorage):
    """Reads behave normally; every write raises."""

    def upload_file(self, key, path):
        raise ConnectionError("storage unreachable")


def _config(measures, cadence_minutes=60, datamodel="Example", **extra) -> dict:
    return {"ANOMALY_CONFIG": json.dumps({datamodel: {"measures": measures,
                                                      "cadence_minutes": cadence_minutes,
                                                      **extra}})}


def _profile(measures=("m1",), calendar=NO_CALENDAR, **extra) -> DatamodelProfile:
    with patch.dict(os.environ, _config(list(measures), calendar=list(calendar), **extra)):
        return DatamodelProfile.from_settings("Example")


def _points(entity_id, values, start=T0, step_hours=1):
    return [{"entity_id": entity_id, "raw_measures": dict(v),
             "timestamp": start + timedelta(hours=step_hours * i)}
            for i, v in enumerate(values)]


def _feed(state, profile, entity_id, values, calendar=None):
    """Drives evaluate_point directly, returning the verdicts."""
    return [evaluate_point(state, entity_id, {"m1": v}, calendar or {}, profile)
            for v in values]


# --- The feature vector: what the model actually sees ---------------------------

def test_the_vector_is_measures_then_calendar_then_the_derived_block():
    columns = feature_columns_for(["a", "b"], ["hour"])
    assert columns == ["a", "b", "hour_sin", "hour_cos",
                       "a_delta", "b_delta", "a_rolling_std", "b_rolling_std"]


def test_a_measure_named_like_a_derived_column_is_not_mistaken_for_one():
    """The derived block is located BY POSITION. Matching a `_delta` suffix would
    classify this raw measure as derived - and its own derived column collides
    with it by name, so the sidecar would stop identifying the vector."""
    indices = derived_indices_for(["pressure_delta"], NO_CALENDAR)
    columns = feature_columns_for(["pressure_delta"], NO_CALENDAR)
    assert columns[0] == "pressure_delta"          # the raw measure
    assert 0 not in indices                        # and it is NOT derived
    assert [columns[i] for i in indices] == ["pressure_delta_delta",
                                             "pressure_delta_rolling_std"]


def test_delta_and_rolling_std_use_the_window_as_it_stood_before_this_point():
    from collections import deque
    profile = _profile(measures=("m1",))
    window = {"m1": deque([10, 20, 30], maxlen=5)}
    vector = build_feature_vector({"m1": 999}, profile, {}, window)
    assert vector[0] == 999.0
    assert vector[1] == 999.0 - 30                          # vs the last value, not itself
    assert math.isclose(vector[2], statistics.pstdev([10, 20, 30]))


def test_several_measures_keep_their_configured_order_through_the_vector():
    """With N>1 the index maths is what maps a dimension back to its meaning."""
    profile = _profile(measures=("m1", "m2", "m3"))
    assert profile.feature_columns[:3] == ["m1", "m2", "m3"]
    assert [profile.feature_columns[i] for i in profile.derived_indices] == [
        "m1_delta", "m2_delta", "m3_delta",
        "m1_rolling_std", "m2_rolling_std", "m3_rolling_std"]


# --- Calendar -------------------------------------------------------------------

def test_no_calendar_configured_means_no_calendar_dimensions():
    """The default. A cycle the signal does not have is pure noise diluting the
    distance, so seasonality is opt-in per datamodel."""
    assert calendar_column_names([]) == []
    assert feature_columns_for(["m1"], []) == ["m1", "m1_delta", "m1_rolling_std"]


def test_each_cycle_adds_its_own_sin_cos_pair():
    row = calendar_row(datetime(2026, 3, 15, 6, 0), ["hour", "weekday", "month"])
    assert set(row) == {"hour_sin", "hour_cos", "weekday_sin", "weekday_cos",
                        "month_sin", "month_cos"}
    assert math.isclose(row["hour_sin"], math.sin(2 * math.pi * 6 / 24))
    # March is month 3 -> index 2 of 12
    assert math.isclose(row["month_sin"], math.sin(2 * math.pi * 2 / 12))


def test_the_month_cycle_wraps_december_next_to_january():
    """A yearly cycle only works if the ends meet: December and January must be
    neighbours, which is the whole reason for the sin/cos encoding."""
    december = calendar_row(datetime(2026, 12, 15), ["month"])
    january = calendar_row(datetime(2027, 1, 15), ["month"])
    july = calendar_row(datetime(2026, 7, 15), ["month"])

    def distance(a, b):
        return math.dist([a["month_sin"], a["month_cos"]], [b["month_sin"], b["month_cos"]])

    assert distance(december, january) < distance(december, july)


def test_the_calendar_batch_stays_aligned_with_its_input_by_position():
    """calendar_context returns a LIST, not a dict keyed by timestamp, and
    evaluate_batch zips it with the points. A reorder inside would silently score
    every point against another one's calendar - so feeding the same instants
    backwards must give exactly the reversed rows."""
    timestamps = [datetime(2026, 8, 12, h, 0) for h in (23, 0, 12)]
    rows = calendar_context(timestamps, ["hour"])
    backwards = calendar_context(list(reversed(timestamps)), ["hour"])

    assert len(rows) == len(timestamps)
    assert rows == list(reversed(backwards))
    assert len({tuple(sorted(r.items())) for r in rows}) == 3   # three distinct hours


def test_the_calendar_is_read_in_local_time_not_utc():
    """An hour and a weekday are local-calendar concepts: at UTC+2, 23:00 UTC on a
    Wednesday is 01:00 on Thursday, and taking it raw lands the busiest part of a
    night on the wrong day."""
    utc_23 = datetime(2026, 8, 12, 23, 0)
    row = calendar_context([utc_23], ["hour"])[0]
    assert row != calendar_row(utc_23, ["hour"])            # not the raw UTC hour
    assert row == calendar_row(utc_23 + timedelta(hours=2), ["hour"])  # Madrid, DST


def test_an_unknown_cycle_is_dropped_instead_of_changing_the_dimension():
    with patch.dict(os.environ, _config(["m1"], calendar=["hour", "fortnight"])):
        profile = DatamodelProfile.from_settings("Example")
    assert profile.calendar_cycles == ["hour"]


# --- Running statistics ---------------------------------------------------------

def test_running_stats_match_the_exact_mean_and_deviation_before_decaying():
    values = [5, 3, 8, 10, 2, 7, 6, 9, 1, 4]
    stats = RunningStats(decay_window=None)
    for v in values:
        stats.update(v)
    assert math.isclose(stats.mean, statistics.mean(values))
    assert math.isclose(stats.std, statistics.pstdev(values))


def test_old_data_fades_once_the_decay_window_is_passed():
    """Without decay the mean averages all history: after a real shift it moves by
    ~1/N and the detector freezes."""
    decaying, exact = RunningStats(decay_window=50), RunningStats(decay_window=None)
    for _ in range(200):
        decaying.update(10.0)
        exact.update(10.0)
    for _ in range(50):
        decaying.update(100.0)
        exact.update(100.0)
    assert decaying.mean > exact.mean * 2


def test_the_decay_window_is_a_duration_not_a_number_of_points():
    """30 days is 720 points hourly and 8640 at 5-minute cadence. The cadence comes
    from cadence_minutes, so neither has to be restated."""
    hourly = _profile(cadence_minutes=60, decay_days=30)
    five_minutely = _profile(cadence_minutes=5, decay_days=30)
    assert hourly.decay_window == 720
    assert five_minutely.decay_window == 30 * 24 * 12


# --- Scoring --------------------------------------------------------------------

def test_nothing_is_flagged_before_there_is_a_baseline_to_deviate_from():
    profile = _profile()
    state = DatamodelAnomalyState.new(profile)
    for verdict in _feed(state, profile, "e1", [50] * (profile.min_points_for_decision - 1)):
        assert verdict["isOutlier"] == 0
    assert _feed(state, profile, "e1", [5000])[0]["isOutlier"] == 0


def test_a_value_far_outside_the_learned_range_is_flagged():
    profile = _profile()
    state = DatamodelAnomalyState.new(profile)
    rng = random.Random(0)
    _feed(state, profile, "e1", [50 + rng.uniform(-5, 5) for _ in range(60)])
    assert _feed(state, profile, "e1", [5000])[0]["isOutlier"] == 1


def test_the_detector_is_not_just_returning_a_constant():
    """The trap the audit found in the old suite: asserting isOutlier==0 on a fresh
    state passes just as well if the detector always answers 0. Same model, same
    entity: normal values must score 0 AND the wild one must score 1."""
    profile = _profile()
    state = DatamodelAnomalyState.new(profile)
    rng = random.Random(3)
    _feed(state, profile, "e1", [50 + rng.uniform(-5, 5) for _ in range(60)])

    calm = _feed(state, profile, "e1", [51.0, 49.0, 50.5])
    wild = _feed(state, profile, "e1", [9000])
    assert [v["isOutlier"] for v in calm] == [0, 0, 0]
    assert wild[0]["isOutlier"] == 1


def test_a_flatlined_signal_is_caught_by_its_collapsed_volatility():
    """The combined distance alone does not catch this: the raw value still looks
    normal, and only the derived rolling_std moves."""
    profile = _profile()
    state = DatamodelAnomalyState.new(profile)
    rng = random.Random(1)
    _feed(state, profile, "e1", [50 + rng.uniform(-5, 5) for _ in range(60)])
    assert any(v["isOutlier"] for v in _feed(state, profile, "e1", [50.0] * 12))


def test_one_extreme_dimension_needs_to_persist_before_it_flags():
    """A lone dimension at 2.2 sigma fires on 5.45% of pure-noise points (measured).
    Requiring it twice in a row is what keeps that from being an alarm per shift.
    Birch is left untrained so the combined distance cannot be what fires."""
    profile = _profile()
    state = DatamodelAnomalyState.new(profile)
    rng = random.Random(7)
    for stats in state.feature_stats:
        for _ in range(profile.min_points_for_decision + 5):
            stats.update(rng.uniform(-1, 1))

    normalized = [0.0] * len(state.feature_stats)
    normalized[-1] = 99.0                       # rolling_std, wildly out on its own
    first, distance = score_outlier(state, "e1", normalized, profile)
    assert distance is None                     # no centroid: not the combined check
    assert first == 0
    assert score_outlier(state, "e1", normalized, profile)[0] == 1
    assert state.consecutive_extreme["e1"] >= EXTREME_DIMENSION_MIN_CONSECUTIVE


def test_the_persistence_counter_is_per_entity_not_global():
    """One model, many entities: an extreme reading on one must not count towards
    another's streak."""
    profile = _profile()
    state = DatamodelAnomalyState.new(profile)
    rng = random.Random(7)
    for stats in state.feature_stats:
        for _ in range(profile.min_points_for_decision + 5):
            stats.update(rng.uniform(-1, 1))

    normalized = [0.0] * len(state.feature_stats)
    normalized[-1] = 99.0
    assert score_outlier(state, "e1", normalized, profile)[0] == 0
    assert score_outlier(state, "e2", normalized, profile)[0] == 0   # its own streak
    assert score_outlier(state, "e1", normalized, profile)[0] == 1


def test_normalize_vector_is_zero_until_a_dimension_has_varied():
    stats = [RunningStats(decay_window=None)]
    assert normalize_vector(stats, [42.0]) == [0.0]     # nothing seen
    stats[0].update(10.0)
    assert normalize_vector(stats, [42.0]) == [0.0]     # std still 0
    stats[0].update(20.0)
    assert math.isclose(normalize_vector(stats, [42.0])[0],
                        (42.0 - stats[0].mean) / stats[0].std)


# --- Learning discipline --------------------------------------------------------

def test_an_outlier_does_not_train_the_model_that_judged_it():
    """Learning it raises its own threshold, so each further anomaly has to be
    wilder than the last and a long episode anaesthetises the detector."""
    profile = _profile()
    state = DatamodelAnomalyState.new(profile)
    rng = random.Random(0)
    _feed(state, profile, "e1", [50 + rng.uniform(-5, 5) for _ in range(60)])

    mean_before = state.feature_stats[0].mean
    assert _feed(state, profile, "e1", [5000])[0]["isOutlier"] == 1
    assert state.feature_stats[0].mean == mean_before


def test_a_sustained_shift_is_eventually_accepted_as_the_new_normal():
    """The flip side: refusing to learn for ever would freeze the model the day a
    signal genuinely moves."""
    profile = _profile()
    state = DatamodelAnomalyState.new(profile)
    rng = random.Random(0)
    _feed(state, profile, "e1", [50 + rng.uniform(-5, 5) for _ in range(60)])

    mean_before = state.feature_stats[0].mean
    _feed(state, profile, "e1", [5000] * profile.regime_shift_points)
    assert state.feature_stats[0].mean > mean_before


def test_a_null_or_infinite_measure_never_reaches_the_model():
    profile = _profile()
    state = DatamodelAnomalyState.new(profile)
    assert evaluate_point(state, "e1", {"m1": None}, {}, profile) is None
    assert evaluate_point(state, "e1", {"m1": float("nan")}, {}, profile) is None
    assert evaluate_point(state, "e1", {"m1": "n/a"}, {}, profile) is None
    assert state.distance_stats.count == 0


def test_a_negative_measure_is_perfectly_normal():
    """There is no rule here about what a sane value is: a delta, a temperature or
    a balance are negative by nature. The vertical only rejects what it cannot turn
    into a number."""
    assert is_scorable({"m1": -5.5}, ["m1"]) is True
    profile = _profile()
    state = DatamodelAnomalyState.new(profile)
    assert evaluate_point(state, "e1", {"m1": -5.5}, {}, profile) is not None


# --- Bounded model --------------------------------------------------------------

def test_the_birch_radius_grows_with_the_dimension_count():
    """A fixed radius made almost every point its own subcluster in a normalized
    space (measured: 1715 of 2000 at 7 dims)."""
    assert default_birch_threshold(15) > default_birch_threshold(7)
    assert _profile(measures=("m1", "m2")).feature_columns.__len__() == 6


def test_the_subcluster_count_stays_bounded():
    profile = _profile()
    state = DatamodelAnomalyState.new(profile)
    rng = random.Random(1)
    _feed(state, profile, "e1", [50 + rng.uniform(-10, 10) for _ in range(700)])
    assert len(state.birch.subcluster_centers_) <= MAX_SUBCLUSTERS


def test_the_decision_threshold_needs_more_history_in_more_dimensions():
    """Distances concentrate as dimensions grow: 10 points say nothing about what a
    normal distance looks like in 40 of them."""
    assert _profile(measures=("m1",)).min_points_for_decision == MIN_POINTS_FLOOR
    assert _profile(measures=tuple(f"m{i}" for i in range(10))).min_points_for_decision > 60


# --- evaluate_batch: config, idempotency, isolation ------------------------------

def test_an_unconfigured_datamodel_scores_nothing():
    with patch.dict(os.environ, {"ANOMALY_CONFIG": ""}):
        assert evaluate_batch(_MemoryStorage(), "Example",
                              _points("e1", [{"m1": 10}])) == {}


def test_a_measure_no_entity_publishes_is_reported_and_nothing_is_scored():
    """A typo in the env var would otherwise report every point unscorable, for
    ever, in silence."""
    storage = _MemoryStorage()
    with patch.dict(os.environ, _config(["does_not_exist"])):
        assert evaluate_batch(storage, "Example", _points("e1", [{"m1": 10}])) == {}
    assert storage.files == {}


def test_measures_given_as_a_string_disable_the_datamodel_instead_of_iterating_it():
    """list("m1") is ['m', '1'] - a plausible config mistake with an incomprehensible
    downstream error."""
    with patch.dict(os.environ, {"ANOMALY_CONFIG": json.dumps(
            {"Example": {"measures": "m1", "cadence_minutes": 60}})}):
        from crowd_predictions.config import settings
        assert settings.anomaly().measures_for("Example") == []
        assert settings.anomaly().is_enabled_for("Example") is False


def test_every_point_of_the_batch_gets_a_verdict_keyed_by_entity_and_instant():
    storage = _MemoryStorage()
    points = _points("e1", [{"m1": 10}, {"m1": 12}]) + _points("e2", [{"m1": 90}])
    with patch.dict(os.environ, _config(["m1"])):
        results = evaluate_batch(storage, "Example", points)
    assert set(results) == {(p["entity_id"], p["timestamp"]) for p in points}
    assert all(set(v) == {"isOutlier"} for v in results.values())


def test_all_the_entities_of_a_datamodel_share_one_stored_model():
    """One bundle per datamodel, not per entity: no per-entity file to collide, and
    the storage traffic stops scaling with the entity count."""
    storage = _MemoryStorage()
    points = [p for e in ("e1", "e2", "e3") for p in _points(e, [{"m1": 10}])]
    with patch.dict(os.environ, _config(["m1"])):
        evaluate_batch(storage, "Example", points)
    models = [k for k in storage.files if k.endswith(".pkl")]
    assert len(models) == 1
    assert models[0].endswith("anomaly_Example.pkl")


def test_each_entity_keeps_its_own_recent_window_inside_the_shared_model():
    """A delta needs THIS entity's previous value; mixing them would invent jumps."""
    storage = _MemoryStorage()
    points = _points("e1", [{"m1": 10}, {"m1": 11}]) + _points("e2", [{"m1": 900}, {"m1": 901}])
    with patch.dict(os.environ, _config(["m1"])):
        evaluate_batch(storage, "Example", points)
        profile = DatamodelProfile.from_settings("Example")
        state = anomaly_storage.load_state(storage, profile)
    assert list(state.windows["e1"]["m1"]) == [10, 11]
    assert list(state.windows["e2"]["m1"]) == [900, 901]


def test_rerunning_the_same_window_scores_again_but_does_not_learn_twice():
    """The transform-time learning is retried by Airflow; without the watermark the
    same points were absorbed once per attempt."""
    storage = _MemoryStorage()
    points = _points("e1", [{"m1": 10}, {"m1": 20}])
    with patch.dict(os.environ, _config(["m1"])):
        first = evaluate_batch(storage, "Example", points)
        profile = DatamodelProfile.from_settings("Example")
        after_first = anomaly_storage.load_state(storage, profile).feature_stats[0].count

        second = evaluate_batch(storage, "Example", points)
        after_second = anomaly_storage.load_state(storage, profile).feature_stats[0].count

    assert set(second) == set(first)          # still scored: the caller keeps its columns
    assert after_second == after_first


def test_only_the_genuinely_new_instant_is_learned_when_runs_overlap():
    storage = _MemoryStorage()
    with patch.dict(os.environ, _config(["m1"])):
        profile = DatamodelProfile.from_settings("Example")
        evaluate_batch(storage, "Example", _points("e1", [{"m1": 10}] * 3))
        before = anomaly_storage.load_state(storage, profile).feature_stats[0].count
        evaluate_batch(storage, "Example", _points("e1", [{"m1": 10}] * 4))
        after = anomaly_storage.load_state(storage, profile).feature_stats[0].count
    assert after == before + 1


def test_a_run_that_learns_nothing_writes_nothing():
    storage = _MemoryStorage()
    points = _points("e1", [{"m1": 10}])
    with patch.dict(os.environ, _config(["m1"])):
        evaluate_batch(storage, "Example", points)
        written = dict(storage.files)
        evaluate_batch(storage, "Example", points)
    assert storage.files == written


def test_the_watermark_advances_even_when_the_point_was_an_outlier():
    """An outlier trains nothing but still moves the watermark and the streak
    counter. Not persisting it left a shifted entity flagged for ever on any
    datamodel that publishes one point per run."""
    storage = _MemoryStorage()
    with patch.dict(os.environ, _config(["m1"])):
        profile = DatamodelProfile.from_settings("Example")
        rng = random.Random(0)
        normal = [{"m1": 50 + rng.uniform(-5, 5)} for _ in range(60)]
        evaluate_batch(storage, "Example", _points("e1", normal))

        wild_at = T0 + timedelta(hours=100)
        evaluate_batch(storage, "Example",
                       [{"entity_id": "e1", "raw_measures": {"m1": 9000},
                         "timestamp": wild_at}])
        state = anomaly_storage.load_state(storage, profile)
    assert state.watermarks["e1"] == wild_at
    assert state.consecutive_outliers["e1"] == 1


def test_a_storage_failure_degrades_to_scoring_nothing():
    with patch.dict(os.environ, _config(["m1"])):
        assert evaluate_batch(_FailingUploadStorage(), "Example",
                              _points("e1", [{"m1": 10}])) == {}


# --- Persistence ----------------------------------------------------------------

def test_the_state_round_trips_through_storage():
    storage = _MemoryStorage()
    profile = _profile()
    state = DatamodelAnomalyState.new(profile)
    _feed(state, profile, "e1", [10, 20, 30])
    anomaly_storage.save_state(storage, profile, state)

    loaded = anomaly_storage.load_state(storage, profile)
    assert list(loaded.windows["e1"]["m1"]) == [10, 20, 30]
    assert loaded.feature_stats[0].count == state.feature_stats[0].count


def test_nothing_stored_yet_is_a_cold_start_not_an_error():
    assert anomaly_storage.load_state(_MemoryStorage(), _profile()) is None


def test_changing_the_configured_measures_starts_the_model_fresh():
    """The columns sidecar is what detects it. With one model per datamodel this
    costs every entity's history at once, which is why it is logged as a retrain."""
    storage = _MemoryStorage()
    anomaly_storage.save_state(storage, _profile(measures=("m1",)),
                               DatamodelAnomalyState.new(_profile(measures=("m1",))))
    assert anomaly_storage.load_state(storage, _profile(measures=("m1", "m2"))) is None


def test_changing_the_calendar_also_starts_it_fresh():
    """It changes the vector's dimension just as much as adding a measure does."""
    storage = _MemoryStorage()
    anomaly_storage.save_state(storage, _profile(calendar=[]),
                               DatamodelAnomalyState.new(_profile(calendar=[])))
    assert anomaly_storage.load_state(storage, _profile(calendar=["hour"])) is None


def test_a_corrupt_bundle_starts_fresh_instead_of_killing_the_datamodel_for_ever():
    """The unpickling happens outside model_storage's own try. Uncaught, the bundle
    is never overwritten and the datamodel stays dead on every future run."""
    storage = _MemoryStorage()
    profile = _profile()
    anomaly_storage.save_state(storage, profile, DatamodelAnomalyState.new(profile))
    key = next(k for k in storage.files if k.endswith(".pkl"))
    storage.files[key] = b"not a pickle at all"
    assert anomaly_storage.load_state(storage, profile) is None


def test_a_bundle_from_another_sklearn_version_starts_fresh():
    storage = _MemoryStorage()
    profile = _profile()
    anomaly_storage.save_state(storage, profile, DatamodelAnomalyState.new(profile))
    key = next(k for k in storage.files if k.endswith(".metrics.json"))
    metrics = json.loads(storage.files[key])
    metrics["sklearn_version"] = "0.0.0-from-the-future"
    storage.files[key] = json.dumps(metrics).encode()
    assert anomaly_storage.load_state(storage, profile) is None


# --- The datamodel lock ---------------------------------------------------------

def test_a_second_run_of_the_same_datamodel_is_refused_while_the_first_holds_it():
    storage = _MemoryStorage()
    with anomaly_storage.datamodel_lock(storage, "Example"):
        with pytest.raises(anomaly_storage.DatamodelLocked):
            with anomaly_storage.datamodel_lock(storage, "Example"):
                pass


def test_the_lock_is_released_on_the_way_out_even_after_an_error():
    storage = _MemoryStorage()
    with pytest.raises(RuntimeError):
        with anomaly_storage.datamodel_lock(storage, "Example"):
            raise RuntimeError("boom")
    with anomaly_storage.datamodel_lock(storage, "Example"):
        pass  # free again


def test_two_different_datamodels_do_not_block_each_other():
    storage = _MemoryStorage()
    with anomaly_storage.datamodel_lock(storage, "Example"):
        with anomaly_storage.datamodel_lock(storage, "Other"):
            pass


def test_an_abandoned_lock_expires_instead_of_blocking_for_ever():
    """A pod killed mid-run must not take its datamodel down with it."""
    storage = _MemoryStorage()
    anomaly_storage._write_lock(storage, "Example",
                                {"holder": "dead-run", "acquired_at": 0}, "/tmp")
    with anomaly_storage.datamodel_lock(storage, "Example"):
        pass
