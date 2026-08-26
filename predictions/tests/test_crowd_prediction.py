import os
from datetime import datetime
from unittest.mock import patch

import pytest

from crowd_predictions.crowd_prediction import (
    predict_weekday_curve, backtest_weekday_prediction, generate_synthetic_occupancy_history,
)


@pytest.fixture(autouse=True)
def _utc_calendar(monkeypatch):
    """These fixtures write the hour they mean, so no shift must be applied. The
    UTC->local conversion has its own test below."""
    monkeypatch.setenv("CALENDAR_TIMEZONE", "UTC")


def _history_fixture():
    """3 mondays + 1 tuesday, values known by hand to verify the exact mean."""
    return [
        {"zone_id": "Z01", "timestamp": datetime(2026, 6, 1, 10), "occupancy": 10},   # monday 1, 10h
        {"zone_id": "Z01", "timestamp": datetime(2026, 6, 8, 10), "occupancy": 20},   # monday 2, 10h
        {"zone_id": "Z01", "timestamp": datetime(2026, 6, 15, 10), "occupancy": 30},  # monday 3, 10h
        {"zone_id": "Z01", "timestamp": datetime(2026, 6, 2, 10), "occupancy": 999},  # tuesday - must not count
    ]


def test_predict_averages_only_same_weekday_past_occurrences():
    history = _history_fixture()
    target = datetime(2026, 6, 22, 10)  # the 4th monday - to be predicted
    result = predict_weekday_curve(history, "Z01", target, n_occurrences=4)
    assert result["weekday"] == "Monday"
    assert result["n_occurrences_used"] == 3
    assert result["hourly_prediction"][10] == 20.0  # mean of 10,20,30
    assert result["daily_total_prediction"] == 20.0


def test_predict_never_uses_data_on_or_after_target_date():
    """It must not look at the target day itself nor at the future - only the past."""
    history = _history_fixture()
    # target = june 15 itself (3rd monday) - it must only use the 2 previous ones
    target = datetime(2026, 6, 15, 10)
    result = predict_weekday_curve(history, "Z01", target, n_occurrences=4)
    assert result["n_occurrences_used"] == 2
    assert result["hourly_prediction"][10] == 15.0  # mean of 10 and 20, it does NOT include the 30 of that same day


def test_predict_respects_n_occurrences_limit():
    history = _history_fixture()
    target = datetime(2026, 6, 22, 10)
    result = predict_weekday_curve(history, "Z01", target, n_occurrences=2)
    assert result["n_occurrences_used"] == 2
    assert result["hourly_prediction"][10] == 25.0  # mean of the 2 MOST RECENT ones: 20 and 30


def test_predict_returns_none_for_hours_without_history():
    history = _history_fixture()
    target = datetime(2026, 6, 22, 10)
    result = predict_weekday_curve(history, "Z01", target, n_occurrences=4)
    assert result["hourly_prediction"][3] is None  # there is never data at 3am in the fixture


def test_predict_returns_zero_occurrences_when_no_history_at_all():
    result = predict_weekday_curve([], "Z01", datetime(2026, 6, 22, 10))
    assert result["n_occurrences_used"] == 0
    assert result["daily_total_prediction"] is None


def test_backtest_computes_mae_against_real_holdout_value():
    history = _history_fixture()
    holdout = datetime(2026, 6, 15, 10)  # 3rd monday, real value = 30
    result = backtest_weekday_prediction(history, "Z01", holdout, n_occurrences=4)
    # prediction = mean of monday 1 and 2 (10, 20) = 15; real = 30 -> error = 15
    assert result["hourly_comparison"][10]["predicted"] == 15.0
    assert result["hourly_comparison"][10]["actual"] == 30
    assert result["mae"] == 15.0


def test_synthetic_history_has_weekday_pattern_weekends_higher():
    """Sanity check of the synthetic fixture: weekends (sat/sun) must come out with a
    higher average crowd count than a typical weekday, otherwise the model has no
    real pattern to learn."""
    history = generate_synthetic_occupancy_history("Z01", weeks=6, seed=1)
    from collections import defaultdict
    by_weekday = defaultdict(list)
    for h in history:
        by_weekday[h["timestamp"].weekday()].append(h["occupancy"])
    avg_by_weekday = {wd: sum(vals) / len(vals) for wd, vals in by_weekday.items()}
    weekend_avg = (avg_by_weekday[5] + avg_by_weekday[6]) / 2
    weekday_avg = sum(avg_by_weekday[d] for d in range(5)) / 5
    assert weekend_avg > weekday_avg


def test_backtest_on_synthetic_history_beats_naive_zero_baseline():
    """The model (mean of the same day of the week) must predict better than not
    predicting anything (a MAE lower than the real mean value itself, a sign that
    it contributes something, not just noise)."""
    history = generate_synthetic_occupancy_history("Z01", weeks=8, seed=2)
    mondays = sorted({h["timestamp"] for h in history if h["timestamp"].weekday() == 0})
    holdout = mondays[-1]
    result = backtest_weekday_prediction(history, "Z01", holdout, n_occurrences=4)
    actual_values = [c["actual"] for c in result["hourly_comparison"].values()]
    naive_mae = sum(actual_values) / len(actual_values)  # predicting "the mean of everything" as a dumb reference
    assert result["mae"] < naive_mae


def test_the_baseline_bins_on_the_local_calendar_not_raw_utc():
    """The bug this guards: binned in raw UTC, a 23:30 UTC reading landed on the wrong
    LOCAL day, so the baseline was compared against the model with a handicap the model
    (training_data.local_calendar_timestamps) does not have."""
    history = [
        # 23:30 UTC on a sunday IS monday 01:30 in Madrid - the reading the monday
        # prediction has to average.
        {"zone_id": "Z01", "timestamp": datetime(2026, 6, 7, 23, 30), "occupancy": 40},
    ]
    target = datetime(2026, 6, 15, 1, 30)   # a monday

    with patch.dict(os.environ, {"CALENDAR_TIMEZONE": "Europe/Madrid"}):
        result = predict_weekday_curve(history, "Z01", target, n_occurrences=4)
    assert result["n_occurrences_used"] == 1
    assert result["hourly_prediction"][1] == 40.0      # 01h local, not 23h

    with patch.dict(os.environ, {"CALENDAR_TIMEZONE": "UTC"}):
        result = predict_weekday_curve(history, "Z01", target, n_occurrences=4)
    assert result["n_occurrences_used"] == 0           # stays on sunday, never counted
