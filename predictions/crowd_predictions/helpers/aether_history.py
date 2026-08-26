"""
Live occupancy history from the platform, in the shape training_data.py expects:
[{"device_id": str, "timestamp": naive datetime, "occupancy": int}] - the shape
the feature functions in training_data.py expect, unchanged.

Timestamps are naive on purpose: one aware value turns the pandas column into
"object" and breaks the exact-timestamp lag/rolling lookups.

THREE different windows, and mixing them up is the easy mistake:

  cold start   COLD_START_DAYS = 365 days. What a full retrain reads.
  prediction   28 + TRAINING_HOLDOUT_DAYS + 7 days (49 by default), see
               minimum_window_hours() and incremental_window_hours(). This is the ONLY
               one INCREMENTAL_HOURS affects, despite living in TrainingSettings: the
               warm start always passes an explicit window_hours, which wins. A shorter
               value is raised to the floor with a warning. Parking's 504 h are not
               enough here - it has no 28-day features. Measured, see tests/test_aether.py.
  warm start   28 (lookback for the features) + INCREMENTAL_TRAIN_DAYS = 30 days, see
               incremental_training_window_hours(). No holdout to validate here because
               nothing is re-tuned.

Below 7 days `lag_1w` is NaN everywhere and there is nothing left to train with;
between 7 and 28, rolling_*_28d comes out NaN and drops out of the feature
set on its own - the model trains with fewer features instead of with a "28-day
mean" computed over 3 days.
"""

import logging
from datetime import datetime, timedelta, timezone

import pandas as pd

from crowd_predictions.config import settings
from crowd_predictions.helpers import aether
# Single source of truth: the same 7 days that the feature selection demands of the
# rows that survive dropna.
from crowd_predictions.training_data import MIN_USABLE_TRAINING_DAYS

logger = logging.getLogger(__name__)

# ENTITY_TYPE / CROWD_MEASURE_ID and their defaults live in config/settings.py.

# Suffix of the entities WE publish (see etl/predict/transform.py). Autodiscovery
# has to skip them or the model would be trained on its own output - a feedback
# loop that looks like it works and drifts away from reality. Same guard as
# the reference prediction ETL.
PREDICTION_ENTITY_SUFFIX = "_pred"

# Cold start: no model / full retrain -> read everything worth reading. A year
# also gives the calendar features (is_holiday, is_high_season, month) at least
# one full cycle of each season.
COLD_START_DAYS = 365

# See the module docstring for these numbers.
# Warm-up so rolling_mean_28d / rolling_std_28d cover a real 28-day window. Below it
# they are NaN, so a shorter window does not degrade the model: it DROPS those two
# features. Correct, but not what anybody wants.
ROLLING_WARMUP_DAYS = 28
# HARD cliff: lag_1w is NaN for every row of the first week, and dropna() removes
# it. Under this, the training table comes out completely empty.
LAG_HARD_MINIMUM_DAYS = 7
# TRAINING_HOLDOUT_DAYS / INCREMENTAL_TRAIN_DAYS and their defaults: config/settings.py.

BIN_MINUTES = 60


class NoHistoryError(RuntimeError):
    """The query worked but there is no usable history.

    Its own type so the entry points can say "there is no data in the platform
    for these devices/measure" instead of failing later, deep inside XGBoost,
    with an empty DataFrame.
    """


def minimum_window_hours() -> int:
    """Floor of the reading window, in hours (see the module docstring). Depends
    on TRAINING_HOLDOUT_DAYS, so it is computed, not hardcoded: raising the
    holdout without widening the window would quietly starve the training set."""
    holdout_days = settings.training().TRAINING_HOLDOUT_DAYS
    return (ROLLING_WARMUP_DAYS + holdout_days + MIN_USABLE_TRAINING_DAYS) * 24


def incremental_window_hours() -> int:
    """INCREMENTAL_HOURS, never below minimum_window_hours(). The default IS the
    floor: there is no sensible value under it, and picking a shorter one is the
    documented way to break training without any error."""
    floor = minimum_window_hours()
    hours = settings.training().INCREMENTAL_HOURS
    if hours is None:
        return floor

    if hours < floor:
        logger.warning(
            f"INCREMENTAL_HOURS={hours} is below the minimum of {floor} h "
            f"({floor // 24} days = {ROLLING_WARMUP_DAYS} of rolling_28d warm-up + holdout + "
            f"{MIN_USABLE_TRAINING_DAYS} usable): raised to {floor}. With a shorter window "
            "dropna(FEATURE_COLUMNS) empties the training table with no error."
        )
        return floor
    return hours


def incremental_train_days() -> int:
    """Days added to the warm start's READING window, on top of the 28 of lookback.
    NOT the days of rows it trains on: it trains with every usable row of the window
    minus the last one (see train_pipeline.train_incremental)."""
    return max(1, settings.training().INCREMENTAL_TRAIN_DAYS)


def incremental_training_window_hours() -> int:
    """
    Window of the WARM START, which is not the one above: with no re-tuning there is
    no holdout to validate, so 28 days of lookback for the features plus
    incremental_train_days() of rows to train/measure is enough (30 days by default).

    The 28 cannot be lowered: rolling_*_28d would come out NaN and the feature would
    drop out of the set, which forces a full retrain (see train.py).
    """
    return (ROLLING_WARMUP_DAYS + incremental_train_days()) * 24


def history_window(incremental: bool = False, now: datetime = None,
                   window_hours: int = None) -> tuple:
    """
    (start_date, end_date) as ISO UTC strings, ready for helpers/aether.py.

    window_hours wins over `incremental`: the warm start has its OWN window
    (incremental_training_window_hours()), narrower than the prediction one.
    incremental=False -> COLD_START_DAYS back (full history).
    incremental=True  -> incremental_window_hours() back (already floored).
    """
    now = now or datetime.now(timezone.utc)
    if window_hours:
        start = now - timedelta(hours=window_hours)
    elif incremental:
        start = now - timedelta(hours=incremental_window_hours())
    else:
        start = now - timedelta(days=COLD_START_DAYS)
    fmt = "%Y-%m-%dT%H:%M:%S.000Z"
    return start.strftime(fmt), now.strftime(fmt)


def entity_type() -> str:
    return settings.aether().ENTITY_TYPE


def measure_id() -> str:
    return settings.aether().CROWD_MEASURE_ID


def _resolve_entity_ids(entity_type_: str, explicit_ids: list, what: str,
                        explicit_setting_name: str) -> list:
    """
    Shared by resolve_device_ids()/resolve_zone_ids(): explicit ids win; otherwise
    discovered from the broker. Entities ending in PREDICTION_ENTITY_SUFFIX are
    excluded: they are our own output. Raises NoHistoryError rather than
    "predicting" zero entities in silence.

    `what`/`explicit_setting_name` are only for the log/error messages (e.g.
    "sensor"/"DEVICE_IDS" vs "zone"/"ZONE_IDS").
    """
    if explicit_ids:
        logger.info(f"{explicit_setting_name} set explicitly: {len(explicit_ids)} {what}(s), "
                    "no autodiscovery")
        return explicit_ids

    logger.info(f"{explicit_setting_name} is empty: discovering entities of type "
                f"{entity_type_} in the broker")
    entities = aether.get_entities_by_type([entity_type_])
    if entities is None:
        raise NoHistoryError(
            f"Could not query the broker for entities of type '{entity_type_}' "
            f"(see the error above). Set {explicit_setting_name} to skip autodiscovery."
        )

    discovered, skipped = [], []
    for entity in entities:
        entity_id = entity.get("id")
        if not entity_id:
            continue
        if entity_id.endswith(PREDICTION_ENTITY_SUFFIX):
            skipped.append(entity_id)
            continue
        discovered.append(entity_id)

    if skipped:
        logger.info(f"  {len(skipped)} prediction entities ('{PREDICTION_ENTITY_SUFFIX}') skipped: "
                    "they are our own output, not an input")

    if not discovered:
        raise NoHistoryError(
            f"No entity of type '{entity_type_}' discovered in tenant/scope "
            f"{aether.aether_tenant()}/{aether.aether_scope()} "
            f"({len(entities)} returned, {len(skipped)} of them predictions). "
            f"Check FIWARE_TENANT/FIWARE_SCOPE, or set {explicit_setting_name}."
        )

    logger.info(f"  {len(discovered)} {what}(s) discovered")
    return sorted(discovered)


def resolve_device_ids() -> list:
    """The Smart Spot sensors to read (CrowdFlowObserved). See _resolve_entity_ids()."""
    return _resolve_entity_ids(entity_type(), settings.aether().device_id_list(),
                               "sensor", "DEVICE_IDS")


def resolve_zone_ids() -> list:
    """The zones to read (CrowdFlowZone, the fused LIDAR+SmartSpot occupancy per zone -
    see etl/crowd/transform.py). See _resolve_entity_ids()."""
    return _resolve_entity_ids(settings.fusion().CROWD_FLOW_ZONE_ENTITY_TYPE,
                               settings.fusion().zone_id_list(), "zone", "ZONE_IDS")


def time_series_to_bins(df: pd.DataFrame, measure: str = None,
                        bin_minutes: int = BIN_MINUTES, agg: str = "mean",
                        id_column: str = "device_id") -> list:
    """
    Aether DataFrame -> a list of bins {id_column, "timestamp", "occupancy"}.

    The values already arrive hourly, but the resample still matters: the
    exact-timestamp lag lookups only match bins sitting on the hour, and two
    readings in the same hour would collide in the lag index.

    agg: how readings inside a bin collapse - "mean" (default), "last" or "max".
    MEAN and not "last", for two different reasons depending on the measure:
    peopleCount* is a COUNT OVER A WINDOW of minutes, so the last reading of the
    hour is a snapshot of its final minutes rather than that hour's occupancy;
    CrowdFlowZone's `occupancy` is instead a simultaneous max (aforo) already, and the
    mean of the hour's maxima is the representative level of that hour - "last"
    would keep whichever sub-window happened to be sampled last, "max" would keep
    the hour's peak and bias every rolling/lag feature upwards.

    id_column: the key the caller wants the entity id under in the returned
    bins - "device_id" by default (CrowdFlowObserved sensors), "zone_id" for
    CrowdFlowZone zones (see train_pipeline.py/etl/predict/extract.py). The raw
    DataFrame column read from is always "device_id" - that is the platform's
    own wire-format field name for "which entity", regardless of its type (see
    time_series_to_dataframe in helpers/aether.py) - only the OUTPUT key changes.
    """
    measure = measure or measure_id()
    if df.empty:
        return []

    filtered = df[df["measure_name"] == measure]
    if filtered.empty:
        available = sorted(df["measure_name"].unique().tolist())
        logger.error(f"No data for measure '{measure}'. Available: {available}")
        return []

    filtered = filtered.copy()
    filtered["timestamp"] = pd.to_datetime(filtered["timestamp"])
    # UTC -> naive: see the module docstring (mixing aware and naive breaks the
    # dtype of the column further downstream).
    if filtered["timestamp"].dt.tz is not None:
        filtered["timestamp"] = filtered["timestamp"].dt.tz_convert("UTC").dt.tz_localize(None)

    filtered["bin"] = filtered["timestamp"].dt.floor(f"{bin_minutes}min")
    filtered = filtered.sort_values(["device_id", "timestamp"])

    grouped = filtered.groupby(["device_id", "bin"])["value"]
    collapsed = getattr(grouped, agg)().dropna()

    bins = [
        {id_column: device_id, "timestamp": bin_start.to_pydatetime(),
         # round() and not int(): the platform serves floats ("value": 15.0) and
         # truncating would bias every count downwards by up to one person.
         "occupancy": int(round(float(value)))}
        for (device_id, bin_start), value in collapsed.items()
    ]
    bins.sort(key=lambda b: (b[id_column], b["timestamp"]))
    return bins


def load_history_bins(device_ids: list = None, measure: str = None,
                      incremental: bool = False, bin_minutes: int = BIN_MINUTES,
                      agg: str = "mean", window_hours: int = None,
                      id_column: str = "device_id") -> list:
    """
    Entry point for reading live history: resolve entities -> query Aether ->
    return bins. Raises instead of returning an empty list, which downstream
    looks like "the model cannot predict anything".

    id_column: forwarded to time_series_to_bins() - "device_id" (default, Smart
    Spot sensors) or "zone_id" (CrowdFlowZone zones, see train_pipeline.py/
    etl/predict/extract.py). `device_ids` is still the right argument name in
    both cases - it is a list of entity URNs to query, regardless of what they
    represent.
    """
    aether.raise_for_aether_config()

    device_ids = device_ids or resolve_device_ids()
    measure = measure or measure_id()
    start_date, end_date = history_window(incremental=incremental, window_hours=window_hours)

    mode = f"{window_hours} h" if window_hours else ("INCREMENTAL" if incremental else "FULL")
    logger.info(f"Reading history from Aether ({mode}): {len(device_ids)} {id_column}(s), "
                f"measure '{measure}', {start_date} -> {end_date}")

    df = aether.get_time_series_as_dataframe(
        device_ids=device_ids, measure_ids=[measure],
        start_date=start_date, end_date=end_date,
    )

    bins = time_series_to_bins(df, measure=measure, bin_minutes=bin_minutes, agg=agg,
                               id_column=id_column)
    if not bins:
        raise NoHistoryError(
            f"Aether returned NO DATA for measure '{measure}' on {len(device_ids)} {id_column}(s) "
            f"in tenant/scope {aether.aether_tenant()}/{aether.aether_scope()} "
            f"between {start_date} and {end_date}. Entities queried: {device_ids}"
        )

    span_days = (max(b["timestamp"] for b in bins) - min(b["timestamp"] for b in bins)).days
    logger.info(f"History converted to bins: {len(bins)} bins, "
                f"{len({b[id_column] for b in bins})} {id_column}(s), {span_days} days spanned")
    # Neither of the two is an error here: the platform may simply not have more
    # history ingested yet, and widening the window would not help. But both are
    # silent downstream, so they get said out loud at the point where the number
    # of days is actually known.
    if span_days < LAG_HARD_MINIMUM_DAYS:
        logger.error(
            f"Only {span_days} days of real history (< {LAG_HARD_MINIMUM_DAYS}): lag_1w is NaN "
            "for every row and only the calendar features are left, so training will be "
            "refused. More ingested history is needed - widening the reading window "
            "does not help."
        )
    elif span_days < ROLLING_WARMUP_DAYS + MIN_USABLE_TRAINING_DAYS:
        logger.warning(
            f"Only {span_days} days of real history (< {ROLLING_WARMUP_DAYS} + "
            f"{MIN_USABLE_TRAINING_DAYS}): rolling_mean_28d/rolling_std_28d come out NaN and "
            "will drop out of the feature set. Nothing breaks and nothing lies, but the "
            "model trains with fewer features - and the MAE changes meaning the day they "
            "come in."
        )

    return bins
