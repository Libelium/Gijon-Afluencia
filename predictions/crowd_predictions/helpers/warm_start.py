"""
Warm start of the crowd model: the daily CronJob adds N trees over the stored
booster instead of repeating the full 365-day training with hyperparameter tuning.

The mode is decided by the STATE IN STORAGE, not by configuration: no bundle -> cold
(365 days + tuning), bundle -> warm (a 30-day window, xgb_model=booster). Everything
here answers the same question - "may this increment go ahead?" - because every "no"
means falling back to the expensive path, and every one of them has to be visible in
the log.

Three guards that the reference prediction ETL does NOT have, and whose absence is a
silent failure there:
  - a cap on the number of trees (50 a day is ~18000 a year and nobody prunes them),
  - the metric compared against the stored one (parking trains on X_new and scores
    on X_new, so its "accuracy 0.98" is the model marking its own homework),
  - the feature set compared against the stored one.
"""

import logging
from datetime import datetime, timezone

import xgboost as xgb

from crowd_predictions import events_registry, weather
from crowd_predictions.config import settings

logger = logging.getLogger(__name__)

# The three knobs below and the reason behind each default: config/settings.py.


def n_estimators_increment() -> int:
    return settings.training().N_ESTIMATORS_INCREMENT


def max_estimators() -> int:
    return settings.training().MAX_ESTIMATORS


def mae_tolerance() -> float:
    return settings.training().INCREMENTAL_MAE_TOLERANCE


def force_full_retrain() -> bool:
    """FORCE_FULL_RETRAIN=true - the manual escape hatch."""
    return settings.training().FORCE_FULL_RETRAIN


def full_retrain_after_days() -> int:
    return settings.training().FULL_RETRAIN_AFTER_DAYS


def full_retrain_is_due(stored_metrics: dict, now: datetime = None) -> str:
    """
    Empty string if the warm start may go ahead, otherwise the reason.

    Twenty-something increments in a row drag the model towards the last few days:
    each batch of trees only corrects the residuals of the window it was shown. This
    is what re-anchors it on the whole history, on a schedule instead of on a tree
    count - see the constants in config/settings.py for why by age.

    A bundle with no `full_trained_at` (written before this existed) is treated as
    due: better one extra full retrain than never doing another one.
    """
    limit_days = full_retrain_after_days()
    if limit_days <= 0:
        return ""

    stamped = stored_metrics.get("full_trained_at")
    if not stamped:
        return "the stored bundle does not record when it was last fully retrained"

    now = now or datetime.now(timezone.utc)
    try:
        last_full = datetime.fromisoformat(stamped)
    except ValueError:
        return f"'full_trained_at' is unreadable ({stamped!r})"
    if last_full.tzinfo is None:
        last_full = last_full.replace(tzinfo=timezone.utc)

    age_days = (now - last_full).days
    if age_days >= limit_days:
        return (f"the last full retrain was {age_days} days ago "
                f"(FULL_RETRAIN_AFTER_DAYS={limit_days})")
    return ""


def calendar_changed(stored_metrics: dict) -> str:
    """
    Empty string if the stored model was trained with the calendar in use now,
    otherwise the reason.

    Changing CALENDAR_TIMEZONE silently redefines `hour`, `weekday`, `is_weekend` and
    `is_holiday` without renaming a single column, so blocking_column_change() cannot
    see it: adding trees would mix two different meanings of the same feature in one
    booster. A bundle from before this was recorded is left alone - it is not worth a
    forced retrain on a value we cannot compare.
    """
    stored = stored_metrics.get("calendar_timezone")
    current = settings.calendar().CALENDAR_TIMEZONE
    if stored and stored != current:
        return f"CALENDAR_TIMEZONE changed ({stored} -> {current})"
    return ""


def weather_availability_changed(stored_metrics: dict) -> str:
    """
    Empty string if unchanged, otherwise the reason - same shape as
    calendar_changed, for the same reason. The day weather gets configured for
    this tenant (WEATHER_LAT/LON or a WEATHER_TARGETS entry), precip_mm flips
    from a constant 0.0 on every row to real values - a warm start would add
    trees over a booster that learned "it never rains", mixing two meanings of
    the same feature. blocking_column_change cannot see this: the column does
    not change, only what feeds it.

    A bundle with no `weather_available` recorded (trained before this existed)
    is left alone, same as calendar_changed with no `calendar_timezone`.
    """
    stored = stored_metrics.get("weather_available")
    if stored is None:
        return ""
    current = weather.is_available_for_current_tenant()
    if stored != current:
        was = "available" if stored else "unavailable"
        now = "available" if current else "unavailable"
        return f"weather availability changed ({was} -> {now})"
    return ""


def events_registry_changed(storage, stored_metrics: dict) -> str:
    """
    Empty string if unchanged, otherwise the reason. Unlike weather (which only
    ever flips once, off -> on), the events registry can change on ANY day, and
    RETROACTIVELY: recording an event for a date already trained on rewrites
    event_magnitude on rows the stored trees already learned as 0 -
    blocking_column_change cannot see it, the column is the same, only its past
    values changed meaning.

    Covers both edits to the registry FILE and re-weighing an event type: the
    fingerprint hashes each row's magnitude, not its event_type.

    A bundle with no `events_fingerprint` recorded is left alone, same
    reasoning as the other two guards. `storage` is the caller's (not
    get_storage()), same reason as train_pipeline._metrics() - a test's fake
    storage, not a real S3 client it never configured. load_events_registry
    already treats a broken/unreachable storage as an empty registry on its
    own (see its own except), so nothing else to guard here.
    """
    stored = stored_metrics.get("events_fingerprint")
    if not stored:
        return ""
    events = events_registry.load_events_registry(storage)
    current = events_registry.fingerprint(events)
    if stored != current:
        return f"events registry changed ({stored} -> {current})"
    return ""


def n_trees(model) -> int:
    """Trees ACTUALLY in the booster. Not model.n_estimators: after load_model() it
    comes back as None, and after a warm start it only holds the new ones."""
    return int(model.get_booster().num_boosted_rounds())


def room_for_more_trees(model, increment: int = None) -> bool:
    """Whether the increment fits under MAX_ESTIMATORS."""
    increment = n_estimators_increment() if increment is None else increment
    return n_trees(model) + increment <= max_estimators()


def blocking_column_change(stored_train_columns: list, current_train_columns: list) -> str:
    """
    Empty string if the increment can go ahead, otherwise the reason.

    Two different changes, both of which invalidate the booster:
      - the feature set: the history now supports a different one, so the new
        trees would see other columns.
      - a NEW zone: the warm start would only add trees over a short window, so the
        zone would stay under-represented; a full retrain gives it the whole
        history. A zone that DISAPPEARS is fine (its column stays at 0).

    NOT because of the one-hot dummy: it was MEASURED that the zone_* columns take
    part in ZERO splits - the rolling features are per zone and already carry its
    level, so the dummy is redundant. Do not "optimise" this guard away on the
    strength of that: what matters is how much history the new zone trains on.
    """
    new_columns = [c for c in current_train_columns if c not in stored_train_columns]
    missing = [c for c in stored_train_columns if c not in current_train_columns]
    features_changed = [c for c in new_columns + missing if not c.startswith("zone_")]

    if features_changed:
        return f"the feature set changed ({features_changed})"
    if new_columns:
        return f"new zones with no column in the stored model ({new_columns})"
    return ""


def metric_got_worse(new_mae: float, previous_mae: float) -> bool:
    """Whether the MAE after the increment is worse than before it, beyond the
    tolerance. Both measured over the SAME held-out day (see train.py). Unknown
    baseline -> False (nothing to compare)."""
    if previous_mae is None or new_mae is None:
        return False
    return new_mae > previous_mae * mae_tolerance()


def warm_start_fit(stored_model, X, y, params: dict, increment: int = None):
    """
    `increment` new trees on top of the stored booster (xgb_model=, which the native
    JSON supports). `params` are the ones the model was trained with (the metrics
    sidecar): growing the trees with a different objective/depth would mix two
    models into one file.

    X has to carry EXACTLY the columns of the stored model, in the same order -
    otherwise XGBoost fails with a feature_names mismatch, which here is the useful
    behaviour and not a nuisance.
    """
    increment = n_estimators_increment() if increment is None else increment
    params = {**params, "n_estimators": increment}
    model = xgb.XGBRegressor(**params)
    model.fit(X, y, xgb_model=stored_model.get_booster())
    return model
