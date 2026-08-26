import os
from datetime import date, datetime, timedelta
from unittest.mock import patch

import pandas as pd

from crowd_predictions.training_data import (
    add_calendar_features, add_lag_features, add_rolling_features,
    clear_caches, feature_columns_from_train_columns, has_minimum_features,
    select_feature_columns, usable_span_days, FEATURE_COLUMNS, TARGET_COLUMN,
    _cached_events_registry, _cached_weather_cache,
)


def test_calendar_features_cyclical_encoding_wraps_around_midnight():
    """Hour 23 and hour 0 must end up CLOSE in the sin/cos space (circular
    continuity) - the real reason for using sine/cosine instead of the hour as an
    integer."""
    bins = [
        {"zone_id": "X", "timestamp": datetime(2026, 6, 1, 23, 0), "occupancy": 5},
        {"zone_id": "X", "timestamp": datetime(2026, 6, 2, 0, 0), "occupancy": 5},
    ]
    df = add_calendar_features(bins)
    dist = ((df["hour_sin"][0] - df["hour_sin"][1]) ** 2 + (df["hour_cos"][0] - df["hour_cos"][1]) ** 2) ** 0.5
    assert dist < 0.3  # they should be very close, not at opposite extremes


def test_calendar_features_weekend_flag():
    bins = [
        {"zone_id": "X", "timestamp": datetime(2026, 6, 1, 10, 0), "occupancy": 1},  # monday
        {"zone_id": "X", "timestamp": datetime(2026, 6, 6, 10, 0), "occupancy": 1},  # saturday
    ]
    df = add_calendar_features(bins)
    assert df["is_weekend"].tolist() == [0, 1]


def test_is_holiday_flags_fixed_national_holiday():
    bins = [
        {"zone_id": "X", "timestamp": datetime(2026, 1, 1, 10, 0), "occupancy": 1},  # New Year
        {"zone_id": "X", "timestamp": datetime(2026, 1, 2, 10, 0), "occupancy": 1},  # a normal day
    ]
    df = add_calendar_features(bins)
    assert df["is_holiday"].tolist() == [1, 0]


def test_is_holiday_flags_moving_easter_based_holiday_without_any_hardcoded_date():
    """The real reason for using the holidays library instead of a hand-written list
    of dates: Maundy Thursday/Good Friday move every year (they depend on the date
    of Easter) - this proves they are detected by themselves, without anybody
    maintaining the exact 2026 date in the code."""
    bins = [
        {"zone_id": "X", "timestamp": datetime(2026, 4, 3, 10, 0), "occupancy": 1},  # Good Friday 2026
        {"zone_id": "X", "timestamp": datetime(2026, 4, 4, 10, 0), "occupancy": 1},  # a normal saturday
    ]
    df = add_calendar_features(bins)
    assert df["is_holiday"].tolist() == [1, 0]


def test_is_holiday_eve_flags_day_before_a_holiday():
    bins = [
        {"zone_id": "X", "timestamp": datetime(2025, 12, 31, 20, 0), "occupancy": 1},  # New Year eve
        {"zone_id": "X", "timestamp": datetime(2026, 1, 1, 20, 0), "occupancy": 1},     # the holiday itself, not the eve
    ]
    df = add_calendar_features(bins)
    assert df["is_holiday_eve"].tolist() == [1, 0]


def test_is_high_season_covers_summer_and_christmas_ranges():
    """Declared by the test, not inherited: HIGH_SEASON_RANGES defaults to empty so no
    deployment gets another one's season."""
    bins = [
        {"zone_id": "X", "timestamp": datetime(2026, 7, 15, 10, 0), "occupancy": 1},   # mid summer
        {"zone_id": "X", "timestamp": datetime(2026, 12, 24, 10, 0), "occupancy": 1},  # christmas
        {"zone_id": "X", "timestamp": datetime(2026, 1, 3, 10, 0), "occupancy": 1},    # epiphany (crossing the year)
        {"zone_id": "X", "timestamp": datetime(2026, 3, 15, 10, 0), "occupancy": 1},   # out of season
    ]
    with patch.dict(os.environ, {"HIGH_SEASON_RANGES": "06-15..09-15,12-20..01-06"}):
        df = add_calendar_features(bins)
    assert df["is_high_season"].tolist() == [1, 1, 1, 0]


def test_no_high_season_configured_marks_nothing_instead_of_guessing():
    """The neutral default: the feature is 0 everywhere, so the model ignores it
    rather than using another deployment's season inverted."""
    bins = [{"zone_id": "X", "timestamp": datetime(2026, 7, 15, 10, 0), "occupancy": 1}]
    df = add_calendar_features(bins)
    assert df["is_high_season"].tolist() == [0]


def test_lag_features_1day_and_1week_shift_correctly():
    bins = []
    for day in range(8):
        bins.append({"zone_id": "X", "timestamp": datetime(2026, 6, 1 + day, 10, 0), "occupancy": 10 + day})
    df = add_calendar_features(bins)
    df = add_lag_features(df)

    # day 1 (index 1, occupancy=11): lag_1d = occupancy of day 0 = 10
    row_day1 = df[df["timestamp"] == datetime(2026, 6, 2, 10, 0)].iloc[0]
    assert row_day1["lag_1d"] == 10

    # day 7 (index 7, occupancy=17): lag_1w = occupancy of 7 days ago (day 0) = 10
    row_day7 = df[df["timestamp"] == datetime(2026, 6, 8, 10, 0)].iloc[0]
    assert row_day7["lag_1w"] == 10


def test_lag_features_nan_when_not_enough_history():
    bins = [{"zone_id": "X", "timestamp": datetime(2026, 6, 1, 10, 0), "occupancy": 5}]
    df = add_calendar_features(bins)
    df = add_lag_features(df)
    assert df["lag_1d"].isna().all()
    assert df["lag_1w"].isna().all()


def test_lag_features_independent_per_zone():
    """The lag of one zone must not get mixed with that of another."""
    bins = [
        {"zone_id": "A", "timestamp": datetime(2026, 6, 1, 10, 0), "occupancy": 100},
        {"zone_id": "B", "timestamp": datetime(2026, 6, 1, 10, 0), "occupancy": 1},
        {"zone_id": "A", "timestamp": datetime(2026, 6, 2, 10, 0), "occupancy": 101},
        {"zone_id": "B", "timestamp": datetime(2026, 6, 2, 10, 0), "occupancy": 2},
    ]
    df = add_calendar_features(bins)
    df = add_lag_features(df)
    row_b_day2 = df[(df["zone_id"] == "B") & (df["timestamp"] == datetime(2026, 6, 2, 10, 0))].iloc[0]
    assert row_b_day2["lag_1d"] == 1  # B's one (day 1), not A's 100


def test_rolling_mean_averages_available_past_days_at_same_hour():
    """7 consecutive days, occupancy = 10,11,...,16 - rolling_mean_7d of day 7
    (index 7, occupancy=17) must be the mean of the 7 previous days (10..16)."""
    bins = []
    for day in range(8):
        bins.append({"zone_id": "X", "timestamp": datetime(2026, 6, 1 + day, 10, 0), "occupancy": 10 + day})
    df = add_calendar_features(bins)
    df = add_rolling_features(df, windows=(7,))
    row_day7 = df[df["timestamp"] == datetime(2026, 6, 8, 10, 0)].iloc[0]
    assert row_day7["rolling_mean_7d"] == sum(range(10, 17)) / 7  # mean of 10..16


def test_rolling_mean_is_nan_when_the_window_is_incomplete_instead_of_a_partial_mean():
    """3 days of history for a window of 7 (43% < 75% coverage) -> NaN. It used to
    return the mean of those 3 under the name "rolling_mean_7d": a feature that lies
    in silence, which no null check catches and which nothing downstream can tell
    apart from a real 7-day mean."""
    bins = []
    for day in range(4):
        bins.append({"zone_id": "X", "timestamp": datetime(2026, 6, 1 + day, 10, 0), "occupancy": 10 + day})
    df = add_calendar_features(bins)
    df = add_rolling_features(df, windows=(7,))
    row_day3 = df[df["timestamp"] == datetime(2026, 6, 4, 10, 0)].iloc[0]
    assert pd.isna(row_day3["rolling_mean_7d"])


def test_rolling_mean_tolerates_gaps_up_to_the_coverage_threshold():
    """The threshold is a PERCENTAGE and not "all 28 days" because the gaps are
    legitimate: bins only exist where the zone reported. 6 of the 7 days of the
    window (86%) still give a value, computed over the 6 that do exist."""
    present_days = [0, 1, 2, 3, 4, 6]  # day 5 missing: the zone did not report
    bins = [{"zone_id": "X", "timestamp": datetime(2026, 6, 1 + day, 10, 0), "occupancy": 10}
            for day in present_days]
    bins.append({"zone_id": "X", "timestamp": datetime(2026, 6, 8, 10, 0), "occupancy": 99})
    df = add_calendar_features(bins)
    df = add_rolling_features(df, windows=(7,))
    row_day7 = df[df["timestamp"] == datetime(2026, 6, 8, 10, 0)].iloc[0]
    assert row_day7["rolling_mean_7d"] == 10.0


def test_rolling_min_coverage_is_configurable():
    bins = []
    for day in range(4):
        bins.append({"zone_id": "X", "timestamp": datetime(2026, 6, 1 + day, 10, 0), "occupancy": 10 + day})
    df = add_calendar_features(bins)
    df = add_rolling_features(df, windows=(7,), min_coverage=0.4)  # 3 of 7 = 43% is enough now
    row_day3 = df[df["timestamp"] == datetime(2026, 6, 4, 10, 0)].iloc[0]
    assert row_day3["rolling_mean_7d"] == sum([10, 11, 12]) / 3


def test_rolling_mean_nan_with_zero_history():
    bins = [{"zone_id": "X", "timestamp": datetime(2026, 6, 1, 10, 0), "occupancy": 5}]
    df = add_calendar_features(bins)
    df = add_rolling_features(df, windows=(7,))
    assert df["rolling_mean_7d"].isna().all()


def test_rolling_mean_independent_per_zone():
    bins = []
    for day in range(8):
        bins.append({"zone_id": "A", "timestamp": datetime(2026, 6, 1 + day, 10, 0), "occupancy": 100})
        bins.append({"zone_id": "B", "timestamp": datetime(2026, 6, 1 + day, 10, 0), "occupancy": 1})
    df = add_calendar_features(bins)
    df = add_rolling_features(df, windows=(7,))
    row_b_day7 = df[(df["zone_id"] == "B") & (df["timestamp"] == datetime(2026, 6, 8, 10, 0))].iloc[0]
    assert row_b_day7["rolling_mean_7d"] == 1  # only B's 1, not mixed with A's 100


def test_rolling_std_is_zero_for_a_stable_zone_and_high_for_an_erratic_one():
    """Two zones with the SAME mean (100) but one stable and the other erratic -
    rolling_std must tell them apart even though rolling_mean is identical."""
    stable_values = [95, 105, 98, 102, 100, 97, 103]  # mean 100, little spread
    erratic_values = [50, 150, 60, 140, 55, 145, 100]  # mean ~100, very spread out
    bins = []
    for day, (v_a, v_b) in enumerate(zip(stable_values, erratic_values)):
        bins.append({"zone_id": "STABLE", "timestamp": datetime(2026, 6, 1 + day, 10, 0), "occupancy": v_a})
        bins.append({"zone_id": "ERRATIC", "timestamp": datetime(2026, 6, 1 + day, 10, 0), "occupancy": v_b})
    # an extra day so that rolling_std_7d of the 7 previous days can be read
    bins.append({"zone_id": "STABLE", "timestamp": datetime(2026, 6, 8, 10, 0), "occupancy": 100})
    bins.append({"zone_id": "ERRATIC", "timestamp": datetime(2026, 6, 8, 10, 0), "occupancy": 100})

    df = add_calendar_features(bins)
    df = add_rolling_features(df, windows=(7,))

    row_stable = df[(df["zone_id"] == "STABLE") & (df["timestamp"] == datetime(2026, 6, 8, 10, 0))].iloc[0]
    row_erratic = df[(df["zone_id"] == "ERRATIC") & (df["timestamp"] == datetime(2026, 6, 8, 10, 0))].iloc[0]

    assert row_stable["rolling_mean_7d"] == row_erratic["rolling_mean_7d"] == 100.0
    assert row_stable["rolling_std_7d"] < 10
    assert row_erratic["rolling_std_7d"] > 30
    assert row_erratic["rolling_std_7d"] > row_stable["rolling_std_7d"]


def test_rolling_std_is_zero_with_a_single_day_inside_a_complete_window():
    """POPULATION deviation, not sample: with a single value it gives 0 instead of
    raising. A window of 1 day is the only complete window that contains exactly one
    value - with windows=(7,) the coverage rule would return NaN first, which is a
    different decision and not this one."""
    bins = [
        {"zone_id": "X", "timestamp": datetime(2026, 6, 1, 10, 0), "occupancy": 42},
        {"zone_id": "X", "timestamp": datetime(2026, 6, 2, 10, 0), "occupancy": 7},
    ]
    df = add_calendar_features(bins)
    df = add_rolling_features(df, windows=(1,))
    row_day2 = df[df["timestamp"] == datetime(2026, 6, 2, 10, 0)].iloc[0]
    assert row_day2["rolling_std_1d"] == 0.0
    assert row_day2["rolling_mean_1d"] == 42.0


def test_rolling_std_nan_with_zero_history():
    bins = [{"zone_id": "X", "timestamp": datetime(2026, 6, 1, 10, 0), "occupancy": 5}]
    df = add_calendar_features(bins)
    df = add_rolling_features(df, windows=(7,))
    assert df["rolling_std_7d"].isna().all()


def test_rolling_std_does_not_crash_when_occupancy_column_mixes_real_values_and_none():
    """A real bug: if the DataFrame mixes real bins (occupancy int) with valueless
    "gaps" (occupancy=None, as prediction_features.py does for the future hours to
    predict), pandas converts the whole column to float64 and the None becomes
    NaN - a "v is not None" filter does NOT exclude NaN (NaN is not None == True),
    so it slips into statistics.pstdev() and blows up. Found while predicting with
    a horizon of more than 24h."""
    bins = []
    for day in range(8):
        bins.append({"zone_id": "X", "timestamp": datetime(2026, 6, 1 + day, 10, 0), "occupancy": 10 + day})
    bins.append({"zone_id": "X", "timestamp": datetime(2026, 6, 9, 10, 0), "occupancy": None})  # future gap

    df = add_calendar_features(bins)
    df = add_rolling_features(df, windows=(7,))  # must not raise AttributeError

    row_gap = df[df["timestamp"] == datetime(2026, 6, 9, 10, 0)].iloc[0]
    assert row_gap["rolling_mean_7d"] > 0  # computed with the 7 real days, ignoring the gap itself


def _hourly_table(n_days, zone_ids=("A", "B")):
    """Hourly bins over `n_days`, the real shape of the history (one bin per zone
    and hour), with the features already computed."""
    bins = [{"zone_id": zone_id, "timestamp": datetime(2026, 1, 1) + timedelta(days=d, hours=h),
             "occupancy": 10 + h}
            for zone_id in zone_ids for d in range(n_days) for h in range(24)]
    df = add_calendar_features(bins)
    df = add_lag_features(df)
    return add_rolling_features(df)


def test_select_feature_columns_grows_with_the_available_history():
    """The tier is a CONSEQUENCE of which features survive, not a table of
    thresholds. The 28-day ones come in on their own once the history
    reaches 28 + 7 days (the coverage rule needs 21 past days, and 7 days of rows
    have to be left to train with)."""
    five_days = select_feature_columns(_hourly_table(5))
    fifteen_days = select_feature_columns(_hourly_table(15))
    sixty_days = select_feature_columns(_hourly_table(60))

    # 5 days: only the calendar features, which need no history at all. Not even
    # lag_1d survives - it costs the first day, and with 5 days there is nothing to
    # spare. That is exactly the tier where train.py refuses to train.
    assert five_days == ["hour_sin", "hour_cos", "weekday_sin", "weekday_cos", "is_weekend",
                          "month", "is_holiday", "is_holiday_eve", "is_high_season",
                          "event_magnitude", "precip_mm"]
    assert "lag_1w" in fifteen_days and "rolling_mean_7d" in fifteen_days
    assert "rolling_mean_28d" not in fifteen_days and "rolling_std_28d" not in fifteen_days
    assert sixty_days == FEATURE_COLUMNS  # all 17


def test_select_feature_columns_keeps_the_declared_order_not_the_tier_order():
    """prepare_features() builds the X matrix in this order and the model stores it
    in its sidecar: two runs with the same history must produce the same order, or
    the reindex at prediction time silently shuffles the columns."""
    selected = select_feature_columns(_hourly_table(60))
    assert selected == [c for c in FEATURE_COLUMNS if c in selected]


def test_select_feature_columns_rejects_a_feature_that_leaves_too_few_rows():
    """27 days: rolling_*_28d IS computable on the last day (21 past days exist), but
    demanding it leaves only 6 days of rows. Better a smaller feature set than a
    model trained on almost nothing - and it prevents the dead zone where the run
    would just refuse to train."""
    selected = select_feature_columns(_hourly_table(27))
    assert "rolling_mean_28d" not in selected
    assert "lag_1w" in selected


def test_select_feature_columns_drops_a_feature_that_is_not_computable_at_the_END():
    """The set has to be computable NOW: prediction builds the features at the fresh
    end of the series, so a feature that only worked in the past is useless. Here the
    last day of the table has no bin one week earlier -> no lag_1w."""
    df = _hourly_table(30, zone_ids=("A",))
    last_day = df["timestamp"].max().normalize()
    # A gap in the week before the last day kills lag_1w only for those rows.
    gap = (df["timestamp"] >= last_day - timedelta(days=7)) & (df["timestamp"] < last_day - timedelta(days=6))
    df = df[~gap].reset_index(drop=True)
    df = add_lag_features(df)

    assert "lag_1w" not in select_feature_columns(df)
    assert "lag_1d" in select_feature_columns(df)


def test_has_minimum_features_is_the_7_day_floor():
    assert has_minimum_features(select_feature_columns(_hourly_table(15))) is True
    assert has_minimum_features(select_feature_columns(_hourly_table(5))) is False


def test_feature_columns_from_train_columns_ignores_the_zone_dummies():
    train_columns = ["hour_sin", "lag_1d", "zone_A", "zone_B"]
    assert feature_columns_from_train_columns(train_columns) == ["hour_sin", "lag_1d"]


def test_usable_span_days_counts_dates_not_rows():
    assert usable_span_days(_hourly_table(5, zone_ids=("A",))) == 5


# --- Calendar features come off LOCAL time, not UTC ---

def test_a_night_bin_is_attributed_to_the_local_day_not_the_utc_one():
    """The bins are UTC. At UTC+2 a Sunday 00:30 local is a Saturday 22:30 UTC, so
    taken raw it lands on the wrong DAY - and the nightlife volume is at night."""
    saturday_2230_utc = datetime(2026, 7, 18, 22, 30)   # = Sunday 00:30 in Madrid
    row = add_calendar_features(
        [{"zone_id": "X", "timestamp": saturday_2230_utc, "occupancy": 5}]).iloc[0]

    assert row["weekday"] == 6 and row["is_weekend"] == 1, "should be Sunday, local"
    assert row["hour"] == 0
    # And the stored timestamp is untouched: the lag/rolling lookups match on it.
    assert row["timestamp"] == saturday_2230_utc


def test_the_offset_follows_daylight_saving():
    """+1h in winter, +2h in summer. A fixed offset would be wrong half the year."""
    winter = add_calendar_features(
        [{"zone_id": "X", "timestamp": datetime(2026, 1, 15, 23, 0), "occupancy": 1}]).iloc[0]
    summer = add_calendar_features(
        [{"zone_id": "X", "timestamp": datetime(2026, 7, 15, 23, 0), "occupancy": 1}]).iloc[0]

    assert winter["hour"] == 0   # 23:00 UTC + 1
    assert summer["hour"] == 1   # 23:00 UTC + 2


def test_utc_as_the_timezone_leaves_the_features_as_they_were():
    """The escape hatch, and the way to reproduce a model trained before this."""
    with patch.dict(os.environ, {"CALENDAR_TIMEZONE": "UTC"}):
        row = add_calendar_features(
            [{"zone_id": "X", "timestamp": datetime(2026, 7, 18, 22, 30), "occupancy": 5}]).iloc[0]

    assert row["weekday"] == 5 and row["hour"] == 22   # Saturday, as UTC says


# --- event_magnitude / precip_mm: always computable, never block training ---

def test_event_magnitude_and_precip_default_to_zero_without_a_storage_backend():
    """No STORAGE_TYPE configured (the test environment) -> get_storage() fails,
    caught by _cached_events_registry/_cached_weather_cache -> both features are 0,
    never a crash and never NaN. Unique tenant/scope so this does not collide with
    the lru_cache entry of any other test in the same process."""
    with patch.dict(os.environ, {"FIWARE_TENANT": "t-cold", "FIWARE_SCOPE": "/"}):
        row = add_calendar_features(
            [{"zone_id": "X", "timestamp": datetime(2026, 8, 15, 10, 0), "occupancy": 3}]).iloc[0]

    assert row["event_magnitude"] == 0
    assert row["precip_mm"] == 0.0


def test_event_magnitude_reflects_the_registered_event_for_that_zone_and_local_day():
    events = [{"date": date(2026, 8, 15), "magnitude": 2, "device_ids": {"X"}}]
    with patch.dict(os.environ, {"FIWARE_TENANT": "t-events", "FIWARE_SCOPE": "/"}), \
         patch("crowd_predictions.training_data.get_storage", return_value=object()), \
         patch("crowd_predictions.training_data.events_registry.load_events_registry", return_value=events):
        matching = add_calendar_features(
            [{"zone_id": "X", "timestamp": datetime(2026, 8, 15, 10, 0), "occupancy": 3}]).iloc[0]
        other_zone = add_calendar_features(
            [{"zone_id": "Y", "timestamp": datetime(2026, 8, 15, 10, 0), "occupancy": 3}]).iloc[0]

    assert matching["event_magnitude"] == 2
    assert other_zone["event_magnitude"] == 0


def test_precip_mm_comes_off_the_weather_cache_keyed_by_utc_not_local():
    cache = {"2026-08-15T10:00:00": {"precip_mm": 4.5, "temp_c": 18.0}}
    with patch.dict(os.environ, {"FIWARE_TENANT": "t-weather", "FIWARE_SCOPE": "/"}), \
         patch("crowd_predictions.training_data.get_storage", return_value=object()), \
         patch("crowd_predictions.training_data.weather.load_weather_cache", return_value=cache):
        row = add_calendar_features(
            [{"zone_id": "X", "timestamp": datetime(2026, 8, 15, 10, 0), "occupancy": 3}]).iloc[0]

    assert row["precip_mm"] == 4.5
    assert "temp_c" not in row  # dropped - no reader anywhere, see the comment in add_calendar_features
    assert "temp_c" not in FEATURE_COLUMNS


# --- clear_caches(): a long-lived process must see a write without restarting ---

def test_clear_caches_makes_the_next_call_re_fetch_events():
    calls = []
    with patch.dict(os.environ, {"FIWARE_TENANT": "t-clear-events", "FIWARE_SCOPE": "/"}), \
         patch("crowd_predictions.training_data.get_storage", return_value=object()), \
         patch("crowd_predictions.training_data.events_registry.load_events_registry",
              side_effect=lambda storage: calls.append(1) or []):
        _cached_events_registry("t-clear-events", "/")
        _cached_events_registry("t-clear-events", "/")  # still cached, no second fetch
        assert len(calls) == 1

        clear_caches()
        _cached_events_registry("t-clear-events", "/")  # cache cleared -> re-fetches
        assert len(calls) == 2


def test_clear_caches_makes_the_next_call_re_fetch_weather():
    calls = []
    with patch.dict(os.environ, {"FIWARE_TENANT": "t-clear-weather", "FIWARE_SCOPE": "/"}), \
         patch("crowd_predictions.training_data.get_storage", return_value=object()), \
         patch("crowd_predictions.training_data.weather.load_weather_cache",
              side_effect=lambda storage: calls.append(1) or {}):
        _cached_weather_cache("t-clear-weather", "/")
        _cached_weather_cache("t-clear-weather", "/")
        assert len(calls) == 1

        clear_caches()
        _cached_weather_cache("t-clear-weather", "/")
        assert len(calls) == 2


# --- Real multi-tenant isolation: TWO tenants in the SAME test, same process,
# same lru_cache instance - not just unique names avoiding a collision (every
# other test in this file does that, which proves nothing about isolation) ---

def test_events_cache_does_not_leak_between_two_tenants_in_the_same_process():
    per_tenant_events = {
        "tenant_a-multi": [{"date": date(2026, 8, 15), "magnitude": 2, "device_ids": None}],
        "tenant_b-multi": [{"date": date(2026, 8, 15), "magnitude": 1, "device_ids": None}],
    }

    def fake_load(storage):
        return per_tenant_events[os.environ["FIWARE_TENANT"]]

    with patch("crowd_predictions.training_data.get_storage", return_value=object()), \
         patch("crowd_predictions.training_data.events_registry.load_events_registry", side_effect=fake_load):
        with patch.dict(os.environ, {"FIWARE_TENANT": "tenant_a-multi", "FIWARE_SCOPE": "/"}):
            tenant_a_row = add_calendar_features(
                [{"zone_id": "X", "timestamp": datetime(2026, 8, 15, 10, 0), "occupancy": 3}]).iloc[0]
        with patch.dict(os.environ, {"FIWARE_TENANT": "tenant_b-multi", "FIWARE_SCOPE": "/"}):
            tenant_b_row = add_calendar_features(
                [{"zone_id": "X", "timestamp": datetime(2026, 8, 15, 10, 0), "occupancy": 3}]).iloc[0]

    assert tenant_a_row["event_magnitude"] == 2
    assert tenant_b_row["event_magnitude"] == 1  # NOT tenant_a's 2 - a stale/shared cache would leak this


def test_weather_cache_does_not_leak_between_two_tenants_in_the_same_process():
    per_tenant_cache = {
        "tenant_a-multi-w": {"2026-08-15T10:00:00": {"precip_mm": 4.5, "temp_c": 18.0}},
        "tenant_b-multi-w": {"2026-08-15T10:00:00": {"precip_mm": 0.0, "temp_c": 30.0}},
    }

    def fake_load(storage):
        return per_tenant_cache[os.environ["FIWARE_TENANT"]]

    with patch("crowd_predictions.training_data.get_storage", return_value=object()), \
         patch("crowd_predictions.training_data.weather.load_weather_cache", side_effect=fake_load):
        with patch.dict(os.environ, {"FIWARE_TENANT": "tenant_a-multi-w", "FIWARE_SCOPE": "/"}):
            tenant_a_row = add_calendar_features(
                [{"zone_id": "X", "timestamp": datetime(2026, 8, 15, 10, 0), "occupancy": 3}]).iloc[0]
        with patch.dict(os.environ, {"FIWARE_TENANT": "tenant_b-multi-w", "FIWARE_SCOPE": "/"}):
            tenant_b_row = add_calendar_features(
                [{"zone_id": "X", "timestamp": datetime(2026, 8, 15, 10, 0), "occupancy": 3}]).iloc[0]

    assert tenant_a_row["precip_mm"] == 4.5
    assert tenant_b_row["precip_mm"] == 0.0  # NOT tenant_a's 4.5
