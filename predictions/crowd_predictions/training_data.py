"""
The training table: occupancy bins -> calendar, lag and rolling features, ready for
crowd_xgboost_model.

WHERE THE BINS COME FROM IN PRODUCTION: helpers/aether_history.load_history_bins(),
already aggregated per ZONE and hour (CrowdFlowZone, the fused LIDAR+SmartSpot
occupancy - see etl/crowd/transform.py). add_calendar_features/add_lag_features/
add_rolling_features are called directly on them (see train_pipeline.load_training_table
and prediction_features), and the same three functions serve training and prediction -
that is why a prediction row cannot drift from a training row.
"""

import logging
import math
import statistics
from functools import lru_cache
from datetime import datetime, timedelta

import holidays
import pandas as pd

from crowd_predictions import events_registry, weather
from crowd_predictions.config import settings
from crowd_predictions.config.config import get_storage

logger = logging.getLogger(__name__)

# Region and high season come from HOLIDAYS_* / HIGH_SEASON_RANGES: with the
# wrong region is_holiday does not fail, it marks the wrong days.


@lru_cache(maxsize=None)
def _cached_events_registry(tenant: str, scope: str) -> list:
    """Cached by (tenant, scope), NOT globally - a multi-tenant run (helpers/
    fiware_targets.py) must not freeze one tenant's events for the next one in
    the same process. One storage round-trip per (tenant, scope) per process,
    not per row nor per recursive prediction step.

    Storage unreachable/unconfigured (no STORAGE_TYPE - unit tests build
    feature tables directly from bins, no backend at all) -> [], same
    cold-start contract as an empty registry. add_calendar_features must never
    fail because of this."""
    try:
        events = events_registry.load_events_registry(get_storage())
    except Exception as e:
        logger.warning(f"Events registry unavailable, treating as empty: {e}")
        return []
    logger.info(f"Events registry loaded: {len(events)} events")
    return events


@lru_cache(maxsize=None)
def _cached_weather_cache(tenant: str, scope: str) -> dict:
    """Same reasoning as _cached_events_registry - see its docstring."""
    try:
        cache = weather.load_weather_cache(get_storage())
    except Exception as e:
        logger.warning(f"Weather cache unavailable, treating as empty: {e}")
        return {}
    logger.info(f"Weather cache loaded: {len(cache)} hours")
    return cache


def clear_caches() -> None:
    """
    Invalidates _cached_events_registry/_cached_weather_cache for every
    (tenant, scope) - call after writing to either (an events CRUD write, a
    weather refresh) in a process that keeps running afterwards, so the next
    add_calendar_features() re-fetches instead of serving what was cached
    before the write. A short-lived script (one target, one process, then
    exit) does not need this - there is nothing yet to have gone stale.
    """
    _cached_events_registry.cache_clear()
    _cached_weather_cache.cache_clear()


def local_calendar_timestamps(timestamps: pd.Series, timezone_name: str) -> pd.Series:
    """
    Naive-UTC bins -> naive LOCAL time, for deriving the calendar features only.

    Bins are stored in UTC (see helpers/aether_history.py) but hour, weekday,
    is_weekend and is_holiday are LOCAL-calendar concepts. At UTC+2, a Sunday 00:30
    local is a Saturday 22:30 UTC: taken raw it lands on the wrong DAY, not just the
    wrong hour, and that is where the nightlife volume is.

    Converting UTC -> local is never ambiguous, even across a DST change (the reverse
    direction is). The returned series is made naive again so nothing downstream mixes
    aware and naive timestamps, which breaks the column dtype.
    """
    if timestamps.empty:
        return timestamps
    aware = timestamps.dt.tz_localize("UTC") if timestamps.dt.tz is None else timestamps
    return aware.dt.tz_convert(timezone_name).dt.tz_localize(None)


@lru_cache(maxsize=None)
def holiday_calendar(country: str, subdivision: str = None):
    """
    The `holidays` calendar of a region. Via the library and not a hand-written list
    of dates: it computes the MOVABLE holidays (Easter week) by itself every year.

    Cached by (country, subdivision) and NOT globally: building it is not free and it
    is queried once per row, but a global would freeze the region of whoever called
    first. With no fixed `years=` on purpose - HolidayBase expands the range by
    itself when queried over any date, past or future.
    """
    return holidays.country_holidays(country, subdiv=subdivision or None)

# 75% = a whole week missing out of 28 is still tolerated (sensors go down, and the
# bins only exist where they reported), more than that and the "28-day mean" is
# another feature altogether. Re-exported so a reader of this module finds it here.
DEFAULT_ROLLING_MIN_COVERAGE = settings.DEFAULT_ROLLING_MIN_COVERAGE


def _is_high_season(ts, ranges: list) -> bool:
    """`ranges` = [((month, day), (month, day))] from HIGH_SEASON_RANGES."""
    month_day = (ts.month, ts.day)
    for start, end in ranges:
        if start <= end:
            if start <= month_day <= end:
                return True
        # A range whose end is before its start crosses the year (20 dec - 6 jan).
        elif month_day >= start or month_day <= end:
            return True
    return False


def add_calendar_features(bins: list) -> pd.DataFrame:
    """
    Adds calendar features to the table of bins - cyclic encoding (sin/cos) for
    hour and day of the week, same pattern as core/data_utils.py of
    the reference prediction ETL: a tree does not know that hour 23 is "close" to hour
    0 if you give it as a flat integer, whereas the sine/cosine does capture that
    circular continuity.
    """
    df = pd.DataFrame(bins)
    if df.empty:
        return df

    # Read here, once per call: the region is per deployment and a module-level
    # calendar would freeze the one of whoever imported first.
    calendar_settings = settings.calendar()
    calendar = holiday_calendar(calendar_settings.country(),
                                 calendar_settings.HOLIDAYS_SUBDIVISION)
    high_season_ranges = calendar_settings.high_season_ranges()

    # EVERY calendar feature comes off local time; `timestamp` itself stays UTC
    # because the lag/rolling lookups match on it and the bins are keyed by it.
    local = local_calendar_timestamps(df["timestamp"], calendar_settings.timezone())

    df["hour"] = local.dt.hour
    df["weekday"] = local.dt.weekday  # 0=monday .. 6=sunday
    df["is_weekend"] = df["weekday"].isin([5, 6]).astype(int)
    df["month"] = local.dt.month

    dates = local.dt.date
    df["is_holiday"] = dates.apply(lambda d: d in calendar).astype(int)
    # Holiday eve - people go out more the night before.
    df["is_holiday_eve"] = dates.apply(lambda d: (d + timedelta(days=1)) in calendar).astype(int)
    df["is_high_season"] = local.apply(
        lambda ts: _is_high_season(ts, high_season_ranges)).astype(int)

    # Cached by (tenant, scope): one storage round-trip per deployment per
    # process, not per row nor per recursive prediction step (see the two
    # _cached_* functions above).
    fiware_settings = settings.fiware()
    events = _cached_events_registry(fiware_settings.FIWARE_TENANT, fiware_settings.FIWARE_SCOPE)
    weather_cache = _cached_weather_cache(fiware_settings.FIWARE_TENANT, fiware_settings.FIWARE_SCOPE)

    # An event is a LOCAL-calendar concept too (the market is happening on this
    # local day) - same `dates` (already local) as is_holiday above.
    df["event_magnitude"] = [
        events_registry.event_magnitude_for(zone_id, event_date, events)
        for zone_id, event_date in zip(df["zone_id"], dates)
    ]
    # Weather, in contrast, is keyed by UTC in the cache (weather.py fetches
    # Open-Meteo with timezone=UTC) - `timestamp` itself, not `local`. Only
    # precip_mm is kept: temp_c has no reader anywhere (checked before dropping
    # it) - weather_for() still
    # computes it (harmless, no reason to change that contract), this is just
    # where a genuinely unused column stopped being carried further.
    df["precip_mm"] = [weather.weather_for(ts, weather_cache)["precip_mm"] for ts in df["timestamp"]]

    df["hour_sin"] = df["hour"].apply(lambda h: math.sin(2 * math.pi * h / 24))
    df["hour_cos"] = df["hour"].apply(lambda h: math.cos(2 * math.pi * h / 24))
    df["weekday_sin"] = df["weekday"].apply(lambda d: math.sin(2 * math.pi * d / 7))
    df["weekday_cos"] = df["weekday"].apply(lambda d: math.cos(2 * math.pi * d / 7))

    return df


def add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds, PER DEVICE_ID, the occupancy value of:
      - lag_1d: the same bin 1 day ago (same hour, previous day).
      - lag_1w: the same bin 1 week ago (same day-of-week AND same hour).

    Lookup BY EXACT TIMESTAMP (zone_id, timestamp - N days), not by
    position/row - the bins only exist where the platform reported, so the
    series has GAPS (it is not dense). Shifting by row number (shift(N)) would
    assume a fixed cadence with no gaps and would give wrong day/hour lags as
    soon as one bin was missing - a real error found while testing this with
    sparse data.

    NaN if there is no exact bin at that past timestamp (there were no events
    that hour) - XGBoost handles NaN natively (missing value handling), there is
    no need to impute here.
    """
    if df.empty:
        return df

    df = df.sort_values(["zone_id", "timestamp"]).reset_index(drop=True)
    occupancy_by_key = {(row.zone_id, row.timestamp): row.occupancy for row in df.itertuples(index=False)}

    df["lag_1d"] = [occupancy_by_key.get((row.zone_id, row.timestamp - timedelta(days=1)))
                     for row in df.itertuples(index=False)]
    df["lag_1w"] = [occupancy_by_key.get((row.zone_id, row.timestamp - timedelta(days=7)))
                     for row in df.itertuples(index=False)]

    return df


def rolling_min_coverage() -> float:
    """Fraction of the window's days that must be present for the rolling features
    to give a value. Read per call so a test/deployment can override it."""
    return settings.training().ROLLING_MIN_COVERAGE


def add_rolling_features(df: pd.DataFrame, windows: tuple = (7, 28),
                         min_coverage: float = None) -> pd.DataFrame:
    """
    Adds, PER ZONE_ID, the rolling mean AND the rolling deviation of occupancy
    in the SAME time slot over the last `windows` calendar days
    (rolling_mean_7d/28d, rolling_std_7d/28d by default):
      - rolling_mean: smooths lag_1d/lag_1w, which are a single isolated value and
        get contaminated if that very day happened to have an odd peak/trough
        (a one-off event, a sensor failure).
      - rolling_std: two zones with the SAME mean can be very different - one
        stable day after day, the other erratic (large peaks/troughs). Without
        this the model cannot tell them apart and treats both as equally
        "reliable". POPULATION deviation (it does not require 2+ values like the
        sample one) - with a single day inside the window it gives 0, not
        NaN/an error.

    Same technique as add_lag_features: lookup BY EXACT TIMESTAMP (zone_id,
    timestamp - k days) for k in 1..window, over those that exist - not pandas'
    positional rolling(), because the series has gaps (bins only where there were
    events).

    NaN if fewer than `min_coverage` of the window's days are present, instead of
    averaging the few there are: a partial mean over 2 days called
    "rolling_mean_28d" is a DIFFERENT feature from the one the model learnt, and no
    null check catches it. A fraction and not "all 28 days" because the gaps are
    legitimate (bins only exist where the zone reported).
    """
    if df.empty:
        return df

    min_coverage = rolling_min_coverage() if min_coverage is None else min_coverage
    occupancy_by_key = {(row.zone_id, row.timestamp): row.occupancy for row in df.itertuples(index=False)}

    for window in windows:
        mean_col = f"rolling_mean_{window}d"
        std_col = f"rolling_std_{window}d"
        min_days = max(1, math.ceil(min_coverage * window))
        mean_values = []
        std_values = []
        for row in df.itertuples(index=False):
            past = [occupancy_by_key.get((row.zone_id, row.timestamp - timedelta(days=k)))
                    for k in range(1, window + 1)]
            # pd.notna() on purpose, not "v is not None": if this DataFrame mixes
            # real bins (occupancy int) with future "gaps" (occupancy=None, see
            # prediction_features.py), pandas converts that column to float64 and
            # the None becomes NaN - "NaN is not None" is True, so a filter by
            # identity lets the NaN through and statistics.pstdev() blows up (a
            # real bug found while predicting with horizon_hours > 24).
            past = [v for v in past if pd.notna(v)]
            if len(past) >= min_days:
                mean_values.append(sum(past) / len(past))
                std_values.append(statistics.pstdev(past))
            else:
                mean_values.append(None)
                std_values.append(None)
        df[mean_col] = mean_values
        df[std_col] = std_values

    return df



FEATURE_COLUMNS = ["hour_sin", "hour_cos", "weekday_sin", "weekday_cos", "is_weekend", "month",
                   "is_holiday", "is_holiday_eve", "is_high_season",
                   "event_magnitude", "precip_mm",
                   "lag_1d", "lag_1w", "rolling_mean_7d", "rolling_mean_28d",
                   "rolling_std_7d", "rolling_std_28d"]
TARGET_COLUMN = "occupancy"

# The 7-day tier. Below it only the calendar features (+lag_1d) survive, and that
# is XGBoost approximating what crowd_prediction.py already computes exactly - the
# entry points refuse to train instead of publishing it.
SEVEN_DAY_FEATURE_COLUMNS = ("lag_1w", "rolling_mean_7d", "rolling_std_7d")

# Minimum span of the rows that survive dropna(selected): a feature that leaves
# fewer usable days than this is not worth the rows it costs. Shared with
# helpers/aether_history.py so the reading window and the selection agree.
MIN_USABLE_TRAINING_DAYS = 7

# The last day of the table is what decides "is this feature computable NOW":
# prediction computes the features at that same end, so anything not available
# there is useless however well it filled the past.
SELECTION_TAIL_DAYS = 1
# Deliberately lenient: the table mixes devices, and one gappy sensor must not veto
# a feature for all the others (its own rows drop out on their own).
DEFAULT_MIN_TAIL_COVERAGE = 0.5


def usable_span_days(df: pd.DataFrame) -> int:
    """Number of distinct calendar dates in the table - "days of data", which is
    not len(df) (hourly bins) nor max-min (gaps)."""
    if df.empty:
        return 0
    return int(df["timestamp"].dt.date.nunique())


def select_feature_columns(df: pd.DataFrame, candidates: list = None,
                           tail_days: int = SELECTION_TAIL_DAYS,
                           min_tail_coverage: float = None,
                           min_usable_days: int = MIN_USABLE_TRAINING_DAYS) -> list:
    """
    The features THIS history supports, from the ones that survive - not a table of
    thresholds per number of days. A candidate is kept when it is mostly non-null
    on the last `tail_days` (computable now, i.e. at prediction time) AND adding it
    still leaves `min_usable_days` of rows after dropna.

    Sorted by non-null count so the cheap tiers are tried first: the tiers are
    nested (calendar > lag_1d > 7d > 28d), so the accepted prefix IS the tier the
    history reaches. The 28-day features entering by themselves the day the history
    allows it is the whole point of this function.
    """
    candidates = candidates or FEATURE_COLUMNS
    if df.empty:
        return []

    min_tail_coverage = DEFAULT_MIN_TAIL_COVERAGE if min_tail_coverage is None else min_tail_coverage
    tail_cutoff = df["timestamp"].max() - timedelta(days=tail_days)
    tail = df[df["timestamp"] > tail_cutoff]
    if tail.empty:
        tail = df

    # Capped by the span that actually exists: with less history than the floor no
    # feature could ever pass, and the whole set would come out empty instead of
    # showing the tier the data did reach (the caller is the one that refuses to
    # train, see has_minimum_features).
    floor_days = min(min_usable_days, usable_span_days(df))

    selected = []
    for column in sorted(candidates, key=lambda c: df[c].notna().sum(), reverse=True):
        if tail[column].notna().mean() < min_tail_coverage:
            continue
        if usable_span_days(df.dropna(subset=selected + [column])) < floor_days:
            continue
        selected.append(column)

    return [c for c in candidates if c in selected]  # declared order, not tier order


def has_minimum_features(feature_columns: list) -> bool:
    """Whether the selected set reaches the 7-day tier (see
    SEVEN_DAY_FEATURE_COLUMNS)."""
    return set(SEVEN_DAY_FEATURE_COLUMNS).issubset(feature_columns)


def feature_columns_from_train_columns(train_columns: list) -> list:
    """The feature subset of a model's exact training columns (the .columns.json
    sidecar), i.e. everything that is not a zone_* dummy."""
    return [c for c in FEATURE_COLUMNS if c in train_columns]
