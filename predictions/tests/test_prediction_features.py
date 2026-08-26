from datetime import datetime, timedelta

from crowd_predictions.training_data import FEATURE_COLUMNS
from crowd_predictions.prediction_features import build_future_bins, build_prediction_feature_table, predict_recursive


def _history_40_days(zone_id="X", base=10):
    return [{"zone_id": zone_id, "timestamp": datetime(2026, 1, 1) + timedelta(days=d, hours=12), "occupancy": base + d}
            for d in range(40)]


def test_build_future_bins_one_row_per_zone_and_hour():
    start = datetime(2026, 2, 10, 0, 0)
    bins = build_future_bins(["A", "B"], start, horizon_hours=3)
    assert len(bins) == 6  # 2 zones x 3 hours
    assert all(b["occupancy"] is None for b in bins)
    hours_a = sorted(b["timestamp"] for b in bins if b["zone_id"] == "A")
    assert hours_a == [start, start + timedelta(hours=1), start + timedelta(hours=2)]


def test_build_future_bins_skips_the_hours_that_already_have_real_data():
    """There is nothing to predict where there is a measurement. Emitting the slot
    anyway duplicated that hour: one row for the real bin plus one for the slot, both
    predicted (the first hour of every entity has been seen arriving twice)."""
    start = datetime(2026, 2, 10, 0, 0)
    history = [{"zone_id": "A", "timestamp": start, "occupancy": 7}]
    bins = build_future_bins(["A", "B"], start, horizon_hours=2, history_bins=history)

    keys = {(b["zone_id"], b["timestamp"]) for b in bins}
    assert ("A", start) not in keys          # A already has that hour
    assert ("B", start) in keys              # B does not: same hour, different zone
    assert len(bins) == 3                    # 2 zones x 2 hours - 1 covered


def test_prediction_table_does_not_predict_an_hour_that_already_has_real_data():
    """The regression: the filter used to be `timestamp >= start_ts`, which also
    selected the HISTORY rows dated at start_ts or later - one duplicated row per
    zone, and predicting over an hour with a real measurement."""
    history = _history_40_days()
    start = datetime(2026, 2, 9, 12, 0)  # 12:00 exists in the history (day 39)

    df = build_prediction_feature_table(history, ["X"], start, horizon_hours=1)

    assert len(df) == 0                       # that hour is real: nothing to predict
    assert df.attrs["dropped"] == []          # and it is not reported as a discard either


def test_build_prediction_feature_table_has_all_feature_columns_and_no_leakage():
    """horizon_hours=1 on purpose: the synthetic history only has bins at 12:00 - a
    2nd hour (13:00) would have no computable lag_1d/1w (there is no real bin at
    that hour on any past day) and would get discarded, which is the correct
    behaviour, not what this test wants to check."""
    history = _history_40_days()
    start = datetime(2026, 2, 10, 12, 0)  # day 40 of the history, 12:00 - matches the usual hour
    df = build_prediction_feature_table(history, ["X"], start, horizon_hours=1)

    assert len(df) == 1
    for col in FEATURE_COLUMNS:
        assert col in df.columns
        assert df[col].notna().all()  # with 40 days of history no lag/rolling must be missing
    assert "occupancy" not in df.columns or df["occupancy"].isna().all()  # the future is never "known"


def test_build_prediction_feature_table_drops_rows_without_enough_history_and_reports_them():
    history = [{"zone_id": "X", "timestamp": datetime(2026, 1, 1, 12, 0), "occupancy": 5}]  # a single day
    start = datetime(2026, 1, 2, 12, 0)
    df = build_prediction_feature_table(history, ["X"], start, horizon_hours=1)

    # lag_1w/rolling_mean_28d cannot be computed with a single day of history -> it is discarded
    assert len(df) == 0
    assert len(df.attrs["dropped"]) == 1
    assert df.attrs["dropped"][0]["zone_id"] == "X"


def _history_40_days_hourly(zone_id="X", base=10):
    """One bin EVERY HOUR of every day (not just one hour/day) - needed to test the
    horizon beyond 24h without bins being missing for some other reason."""
    return [
        {"zone_id": zone_id, "timestamp": datetime(2026, 1, 1) + timedelta(days=d, hours=h), "occupancy": base + d}
        for d in range(40) for h in range(24)
    ]


def test_build_prediction_feature_table_caps_at_24h_even_with_dense_hourly_history():
    """Found while predicting with horizon_hours>24 over real data: by design, only
    the first day is predictable NO MATTER how much horizon is asked for.
    lag_1d/lag_1w are computed by lookup against the REAL history
    (occupancy_by_key), and the predictions of later days are not fed back as
    "history" - hour 30 (day 2) would need the lag_1d of hour 6 of day 2, which is
    itself a prediction of ours, not real data, so it does not exist in
    occupancy_by_key and gets discarded. This is not a bug of incomplete data
    (there IS a real bin at every hour of every day of the history here) - it is a
    real design limitation, documented here."""
    history = _history_40_days_hourly()
    start = datetime(2026, 2, 10, 0, 0)  # right after the last day of the history

    df_24h = build_prediction_feature_table(history, ["X"], start, horizon_hours=24)
    assert len(df_24h) == 24  # the whole first day IS predictable

    df_48h = build_prediction_feature_table(history, ["X"], start, horizon_hours=48)
    assert len(df_48h) == 24  # the second day adds NOTHING predictable, it is discarded
    assert len(df_48h.attrs["dropped"]) == 24


def test_build_prediction_feature_table_independent_per_zone():
    history = _history_40_days(zone_id="A", base=100) + _history_40_days(zone_id="B", base=1)
    start = datetime(2026, 2, 10, 12, 0)
    df = build_prediction_feature_table(history, ["A", "B"], start, horizon_hours=1)

    assert set(df["zone_id"]) == {"A", "B"}
    row_a = df[df["zone_id"] == "A"].iloc[0]
    row_b = df[df["zone_id"] == "B"].iloc[0]
    assert row_a["lag_1d"] > row_b["lag_1d"]  # A has base=100, B base=1 - they must not get mixed


def _constant_predict_fn(value):
    return lambda feature_df: [value] * len(feature_df)


def test_predict_recursive_beats_the_24h_cap_by_feeding_its_predictions_forward():
    """The cap and the mechanism that breaks it, in ONE run: each recursive step
    rebuilds the feature table over the growing history, so hours cost ~0.2 s apiece
    and asking for two separate horizons paid the same evidence twice.

    25 hours is the cheapest horizon that proves both:
    - it goes past the ceiling. The NON recursive version returned 24 rows no matter
      the horizon asked for (see
      test_build_prediction_feature_table_caps_at_24h_even_with_dense_hourly_history);
    - it gets there by feedback, not by luck. The row of step 25 is the same day-hour
      as step 1, 24h later, so its lag_1d must be the PREDICTION of step 1 - there is
      no real data point there."""
    history = _history_40_days_hourly()
    start = datetime(2026, 2, 10, 0, 0)

    result = predict_recursive(history, ["X"], _constant_predict_fn(77), start, horizon_hours=25)

    assert len(result) == 25
    assert sorted(result["horizon_step"]) == list(range(1, 26))
    assert result.attrs["dropped"] == []
    step_25 = result[result["horizon_step"] == 25].iloc[0]
    assert step_25["lag_1d"] == 77  # the prediction (constant=77) of step 1, fed back


def test_predict_recursive_reports_dropped_steps_without_crashing():
    history = [{"zone_id": "X", "timestamp": datetime(2026, 1, 1, 12, 0), "occupancy": 5}]  # a single day
    start = datetime(2026, 1, 2, 12, 0)

    result = predict_recursive(history, ["X"], _constant_predict_fn(10), start, horizon_hours=3)

    assert result.empty
    assert len(result.attrs["dropped"]) == 3  # all 3 steps, none with enough history
