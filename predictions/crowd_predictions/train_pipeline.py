"""
Training pipeline of the crowd model (XGBoost, Phase 5). Same container
pattern as main.py (LIDAR+SmartSpot fusion) - meant to run as a Docker image +
Kubernetes CronJob in PRE (see README), a different CMD over the SAME image
("python train.py" instead of "python main.py").

Training data: read LIVE from the platform, per ZONE (Aether Link -> CrowdFlowZone,
the already-fused LIDAR+SmartSpot occupancy - see helpers/aether_history.py and
etl/crowd/transform.py for where CrowdFlowZone is published). Nothing to mount: this
is what makes the CronJob work without a PVC or an init-container, and the
predictions stop degrading as an export ages.

TWO MODES, decided by the STATE IN STORAGE and not by configuration

  cold  no model in storage (or FORCE_FULL_RETRAIN, or a guard in
        helpers/warm_start.py says no). Reads COLD_START_DAYS (365) and trains from
        scratch with hyperparameter tuning - the expensive part, and it is paid once
        PER TARGET.
  warm  there is a bundle: reads a 30-day window and adds N_ESTIMATORS_INCREMENT
        trees over the stored booster. Cheap and daily.

The FEATURE SET is not fixed either: the features are the ones the available
history supports, and the rest come in on their own the day it reaches them. Under
7 days of usable history nothing is trained and NOTHING IS PUBLISHED - a stale
model is better than an entity that is sometimes a model and sometimes an average,
with the consumer unable to tell which one they are reading. The target counts as a
failure (red exit code), same criterion as run_for_each_target.

FIWARE_TARGETS runs the whole cycle once per tenant/scope (helpers/
fiware_targets.py).
"""

import logging
from datetime import datetime, timedelta, timezone

import pandas as pd

from crowd_predictions import events_registry, weather
from crowd_predictions.config import settings
from crowd_predictions.config.config import get_storage
from crowd_predictions.helpers.fiware_targets import run_for_each_target
from crowd_predictions.helpers.model_storage import load_model_bundle, save_model_bundle
from crowd_predictions.helpers.warm_start import (blocking_column_change, calendar_changed,
                                 events_registry_changed, force_full_retrain,
                                 full_retrain_is_due, mae_tolerance, max_estimators,
                                 metric_got_worse, n_estimators_increment, n_trees,
                                 room_for_more_trees, warm_start_fit,
                                 weather_availability_changed)
from crowd_predictions.crowd_xgboost_model import (
    DEFAULT_PARAMS, backtest_by_horizon_step, backtest_spread_by_horizon_step,
    prepare_features, time_based_split, train_model,
    evaluate_model, tune_hyperparameters, compare_against_weekday_baseline,
)
from crowd_predictions.helpers.aether import AetherConfigError
from crowd_predictions.helpers.aether_history import (COLD_START_DAYS, NoHistoryError,
                                     incremental_training_window_hours, load_history_bins,
                                     resolve_zone_ids)
from crowd_predictions.training_data import (add_calendar_features, add_lag_features, add_rolling_features,
                            has_minimum_features, select_feature_columns, usable_span_days,
                            FEATURE_COLUMNS, SEVEN_DAY_FEATURE_COLUMNS, TARGET_COLUMN)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Days of rows the warm start uses: the last one measures, the rest train. Parking
# does not set anything aside and evaluates over the very rows it just fitted.
INCREMENTAL_METRIC_DAYS = 1
# Fulls in a row before saying so out loud. 3 = a whole weekend of falling to the
# expensive path without a single warm start landing.
CONSECUTIVE_FULL_RETRAINS_WARNING = 3


def load_training_table(window_hours: int = None):
    """
    The feature table with NO dropna: which columns are usable is decided afterwards
    by select_feature_columns() over this very table, and dropping rows here would
    hide the fact that the history does not reach a feature.

    `window_hours` = the warm start's narrow window; None = the full history.
    """
    bins = load_history_bins(device_ids=resolve_zone_ids(), measure="occupancy",
                             id_column="zone_id", incremental=window_hours is not None,
                             window_hours=window_hours, bin_minutes=60)

    df = add_calendar_features(bins)
    df = add_lag_features(df)
    return add_rolling_features(df)


def usable_training_table(window_hours: int = None):
    """
    (rows that can be trained on, chosen features) or (None, []) if the history does
    not reach the floor - in which case NOTHING is trained and nothing is published.

    The set is logged on every run on purpose: the day rolling_*_28d comes in, the
    MAE changes meaning, and without this line it looks like the model made an
    inexplicable jump.
    """
    df = load_training_table(window_hours=window_hours)
    if df.empty:
        logger.error("The source returned no bins at all: nothing to train with.")
        return None, []

    feature_columns = select_feature_columns(df)
    usable = df.dropna(subset=feature_columns) if feature_columns else df.iloc[0:0]
    logger.info(f"FEATURES IN USE ({len(feature_columns)}/{len(FEATURE_COLUMNS)}): {feature_columns}")
    unavailable = [c for c in FEATURE_COLUMNS if c not in feature_columns]
    if unavailable:
        logger.info(f"  not supported by this history, left out: {unavailable}")
    logger.info(f"  history read: {usable_span_days(df)} days / {len(df)} bins -> "
                f"usable: {usable_span_days(usable)} days / {len(usable)} rows")
    _log_rows_per_zone(df, usable)

    if not has_minimum_features(feature_columns) or usable.empty:
        logger.error(
            f"NOT TRAINING and NOT PUBLISHING: the history does not reach the 7-day tier "
            f"({list(SEVEN_DAY_FEATURE_COLUMNS)}). Only the calendar features are left, and "
            "that is XGBoost approximating what crowd_prediction.py already computes exactly. "
            "The previous model (if there is one) stays in storage untouched; more ingested "
            "history is needed, widening the reading window does not help."
        )
        return None, []
    return usable, feature_columns


def _log_rows_per_zone(df, usable) -> None:
    """How many rows each zone contributes to the JOINT model, by name.

    NOT a quality gate, on purpose. A gate would be redundant: dropna(feature_columns)
    already leaves a zone with too little history at ZERO rows (measured), and
    ROLLING_MIN_COVERAGE already stops a gappy one from getting a fake 28-day mean. What
    was missing is not filtering, it is SEEING it - a zone reporting one hour a day
    contributes real rows, 4% of a healthy one, and nothing said so.
    """
    if usable.empty:
        return
    read = df.groupby("zone_id").size()
    kept = usable.groupby("zone_id").size()
    starved = [z for z in read.index if kept.get(z, 0) == 0]
    share = {z: f"{kept[z]} ({100 * kept[z] / len(usable):.0f}%)" for z in kept.index}
    logger.info(f"  rows per zone: {share}")
    if starved:
        logger.warning(f"  {len(starved)} zone(s) contribute NO usable row and are absent from the "
                       f"model: {starved}. Expected on a newly installed one (it needs 7 days for "
                       "lag_1w); on an old one it means its history has holes.")


def effective_holdout_days(usable) -> int:
    """
    TRAINING_HOLDOUT_DAYS capped to a third of the usable span. With a short history
    the fixed 14 days leave the training set EMPTY (and tuning needs two of these
    windows, val + test), so the run would die for a reason that has nothing to do
    with the data being short.
    """
    span = usable_span_days(usable)
    configured = settings.training().TRAINING_HOLDOUT_DAYS
    holdout = max(1, min(configured, span // 3))
    if holdout != configured:
        logger.warning(f"Holdout reduced from {configured} to {holdout} days: only {span} "
                       "usable days, and a third of them at most can be held out.")
    return holdout


def _metrics(storage, mode: str, results: dict, params: dict, model, usable, holdout_days: int,
             full_trained_at: str = None, consecutive_fulls: int = 0) -> dict:
    """The metrics sidecar. Without it a stored model cannot be warm-started: there
    would be no hyperparameters for the new trees and no MAE to compare against.

    `storage` (the caller's, not get_storage()) so a test's fake storage is what
    gets read for events_fingerprint - not a real S3 client the test never set up.
    """
    now = datetime.now(timezone.utc).isoformat()
    calendar_settings = settings.calendar()
    return {
        "mode": mode,
        "mae": results["mae"],
        "mape_pct": results["mape_pct"],
        "mae_holdout_days": holdout_days,
        "params": params,
        "n_trees": n_trees(model),
        # High-water mark of the DATA, not of the run: it is how the next run knows
        # whether there is anything new, or whether ingestion has stalled and it
        # would be piling up trees over the same rows.
        "latest_data_timestamp": usable["timestamp"].max().isoformat(),
        "trained_at": now,
        # When the model last saw the WHOLE history. A warm start PROPAGATES it
        # instead of re-stamping it, which is what lets the age-based full retrain
        # work - `trained_at` moves on every save and would never look old.
        "full_trained_at": full_trained_at or now,
        # The calendar features are derived in this timezone. Recorded because the
        # COLUMNS do not change when it does, so nothing else could tell that
        # `hour`/`weekday` now mean something different.
        "calendar_timezone": calendar_settings.CALENDAR_TIMEZONE,
        # Same reasoning as calendar_timezone, for the other two features that can
        # silently change MEANING without renaming a column - see
        # warm_start.weather_availability_changed/events_registry_changed.
        "weather_available": weather.is_available_for_current_tenant(),
        "events_fingerprint": events_registry.fingerprint(
            events_registry.load_events_registry(storage)),
        # Full retrains in a row. parking had to MEASURE that its window was too small
        # before it could fix it; this is the number that makes that measurable here.
        # Reset by a successful warm start.
        "consecutive_full_retrains": consecutive_fulls,
    }


def _log_metrics(results: dict, baseline: dict):
    logger.info(f"XGBoost global MAE: {results['mae']}  global MAPE: {results['mape_pct']}%")
    for zone_id, m in results["per_zone"].items():
        base_mae = baseline.get(zone_id)
        logger.info(f"  {zone_id}: MAE={m['mae']} (baseline={base_mae})  MAPE={m['mape_pct']}%")


def train_full(storage, previous_fulls: int = 0) -> int:
    """Cold start: full history, hyperparameter tuning, model from scratch.

    `previous_fulls` = how many fulls in a row preceded this one. A cold start every day
    is not a bug on its own, but it IS the symptom of something to fix upstream (a gappy
    sensor that keeps changing the feature set, a window too narrow), and nothing else in
    the log makes it visible ACROSS runs.
    """
    usable, feature_columns = usable_training_table()
    if usable is None:
        return 1

    holdout_days = effective_holdout_days(usable)
    train_df, test_df = time_based_split(usable, holdout_days=holdout_days)
    logger.info(f"Train: {len(train_df)} rows | Test: {len(test_df)} rows")
    if train_df.empty or test_df.empty:
        logger.error("NOT TRAINING: the temporal split leaves one of the two sides empty.")
        return 1

    tuning = tune_hyperparameters(usable, val_days=holdout_days, test_days=holdout_days,
                                   feature_columns=feature_columns)
    logger.info(f"Best hyperparameters: {tuning['best_params']} (MAE val={tuning['best_val_mae']})")

    params = {**DEFAULT_PARAMS, **tuning["best_params"]}

    # Validation for early stopping, carved out of TRAIN and never out of test_df:
    # picking the number of trees on the holdout is what makes a reported metric
    # optimistic. If the history is too short to afford the slice, train without it -
    # the alternative is a training set that is empty for a reason nobody would guess.
    rounds = settings.training().EARLY_STOPPING_ROUNDS
    fit_df, eval_df = train_df, None
    if rounds > 0:
        candidate_fit, candidate_eval = time_based_split(train_df, holdout_days=holdout_days)
        if not candidate_fit.empty and not candidate_eval.empty:
            fit_df, eval_df = candidate_fit, candidate_eval
            logger.info(f"Early stopping ON: {len(fit_df)} rows to fit, {len(eval_df)} to watch, "
                        f"stopping after {rounds} rounds with no improvement")
        else:
            logger.warning(f"Early stopping OFF: {len(train_df)} train rows do not survive carving "
                           f"a {holdout_days}-day validation slice out of them.")

    model = train_model(fit_df, params=params, feature_columns=feature_columns,
                        eval_df=eval_df, early_stopping_rounds=rounds if eval_df is not None else None)
    if eval_df is not None:
        logger.info(f"Trees kept: {n_trees(model)} of the {params.get('n_estimators')} allowed "
                    f"(best_iteration={model.best_iteration})")
    train_columns = prepare_features(fit_df, feature_columns).columns.tolist()
    results = evaluate_model(model, test_df, train_columns, feature_columns)
    baseline = compare_against_weekday_baseline(usable, holdout_days=holdout_days)
    _log_metrics(results, baseline)

    # The error of the RECURSIVE horizon, which is what actually gets published. Only
    # after a full retrain: it costs one feature-table rebuild per step, and it is the
    # run that already pays for tuning.
    horizon_mae = {}
    backtest_hours = settings.training().BACKTEST_HORIZON_HOURS
    if backtest_hours > 0:
        horizon_mae = backtest_by_horizon_step(model, train_columns, usable.to_dict("records"),
                                                horizon_hours=backtest_hours,
                                                feature_columns=feature_columns)
        if horizon_mae:
            first, last = horizon_mae.get("1"), horizon_mae.get(str(backtest_hours))
            logger.info(f"MAE by horizon step (recursive, {backtest_hours}h): step 1={first}, "
                        f"step {backtest_hours}={last}, overall={horizon_mae.get('overall')} "
                        f"- compare with the one-step MAE above ({results['mae']})")
        else:
            logger.info("Horizon backtest skipped: not enough history behind the window.")

    # The BAND that predict.py publishes around each predicted value. Computed on
    # the same full-retrain run as the MAE above and stored in the same sidecar:
    # predict.py has no history to measure it on, and recomputing it there would
    # cost a backtest per prediction run.
    horizon_spread = {}
    if backtest_hours > 0:
        horizon_spread = backtest_spread_by_horizon_step(
            model, train_columns, usable.to_dict("records"),
            horizon_hours=backtest_hours, feature_columns=feature_columns)
        if horizon_spread:
            first = horizon_spread.get("1") or {}
            logger.info(f"Prediction band by horizon step: step 1 = "
                        f"[{first.get('lo')}, {first.get('hi')}] relative to the predicted "
                        f"value; {len(horizon_spread)} step(s) measured.")
        else:
            logger.info("Prediction band skipped: not enough backtest samples per step.")

    consecutive = previous_fulls + 1
    if consecutive >= CONSECUTIVE_FULL_RETRAINS_WARNING:
        logger.warning(
            f"{consecutive} FULL retrains in a row. Each one reads {COLD_START_DAYS} days and "
            "re-tunes, per target. It is a cost symptom, not a correctness one: look at the reason "
            "logged just above - a sensor whose gaps keep changing the feature set, or a window "
            "too narrow, will keep it here for ever."
        )
    metrics = _metrics(storage, "full", results, params, model, usable, holdout_days,
                       consecutive_fulls=consecutive)
    metrics["mae_by_horizon_step"] = horizon_mae
    metrics["spread_by_horizon_step"] = horizon_spread
    model_path = settings.training().MODEL_OUTPUT_PATH
    model_key = save_model_bundle(storage, model_path, model, train_columns, metrics)
    logger.info(f"COLD training: {n_trees(model)} trees. Bundle uploaded as '{model_key}' "
                f"(+.columns.json +.metrics.json, storage={type(storage).__name__})")
    return 0


def train_incremental(storage, stored_model, stored_columns: list, stored_metrics: dict):
    """
    Warm start: N_ESTIMATORS_INCREMENT trees over the stored booster, using the 30-day
    window (28 of lookback for the features + the new rows), with no re-tuning.

    Returns 0/1, or None meaning "this increment must not go ahead, do a full
    retrain" - every one of those cases is logged with its reason.
    """
    usable, feature_columns = usable_training_table(window_hours=incremental_training_window_hours())
    if usable is None:
        # This WINDOW does not reach the floor, which says nothing about the whole
        # history: a few days of sensors down, or a backfill leaving a gap inside the
        # last 30 days, starve the window while the year behind it is fine. Measured:
        # the same data returns 1 through here and trains fine through train_full.
        # So fall to full and let IT judge over the whole history.
        logger.warning("The incremental window does not reach the usable floor. That says "
                       "nothing about the full history: falling back to a full retrain, which "
                       "reads it all and decides there.")
        return None

    latest_stored = stored_metrics.get("latest_data_timestamp")
    freshest = usable["timestamp"].max()
    if latest_stored and freshest <= pd.Timestamp(latest_stored):
        # Two very different reasons land here, and only one of them is fine.
        training = settings.training()
        stale_days = (datetime.now(timezone.utc).replace(tzinfo=None) -
                      freshest.to_pydatetime()).days
        limit = training.MAX_DATA_STALENESS_DAYS
        if limit > 0 and stale_days >= limit:
            logger.error(
                f"INGESTION LOOKS DEAD: the freshest bin is {stale_days} days old "
                f"(MAX_DATA_STALENESS_DAYS={limit}) and there is nothing new since the last "
                f"training ({latest_stored}). Going RED on purpose - a full retrain over the "
                "same stale rows would also succeed, so nothing else here would ever notice."
            )
            return 1
        logger.warning(f"NO NEW DATA since the last training ({latest_stored}): the model is left "
                       "as it is. Adding trees over the same rows only overfits them.")
        return 0

    # Every usable row of the window trains, minus the last day which measures. NOT
    # only the new day: MEASURED here (see tests/test_train_modes.py), 50 trees over
    # a single day fit that day's residuals and the MAE on the held-out day gets
    # worse, so the guard below would discard every increment and nothing would ever
    # be warm-started. The 28 days behind the window are lookback for the features,
    # not rows - that is why 30 days of reading leave ~10 days of rows.
    train_df, metric_df = time_based_split(usable, holdout_days=INCREMENTAL_METRIC_DAYS)
    if train_df.empty or metric_df.empty:
        logger.warning(f"Warm start not viable: {len(train_df)} rows to train and "
                       f"{len(metric_df)} to measure in the incremental window.")
        return None

    train_columns = prepare_features(train_df, feature_columns).columns.tolist()
    blocking = blocking_column_change(stored_columns, train_columns)
    if blocking:
        logger.warning(f"Warm start ABORTED - {blocking}. The new trees would see columns other "
                       "than the ones in the booster: full retrain instead.")
        return None

    # The SAME day, measured with the old model and with the new one. Comparing
    # against the MAE in the sidecar would be comparing a 14-day holdout against a
    # single day: noisier by construction, and it would force a full retrain every
    # time a bank holiday landed on the measured day.
    before = evaluate_model(stored_model, metric_df, stored_columns, feature_columns)

    X = prepare_features(train_df, feature_columns).reindex(columns=stored_columns, fill_value=0)
    model = warm_start_fit(stored_model, X, train_df[TARGET_COLUMN], stored_metrics["params"])
    logger.info(f"WARM start: {n_trees(stored_model)} trees + {n_estimators_increment()} = "
                f"{n_trees(model)} (cap {max_estimators()}), fitted with {len(train_df)} rows")

    results = evaluate_model(model, metric_df, stored_columns, feature_columns)
    baseline = compare_against_weekday_baseline(usable, holdout_days=INCREMENTAL_METRIC_DAYS)
    _log_metrics(results, baseline)
    logger.info(f"MAE on the held-out day: {before['mae']} before the increment -> "
                f"{results['mae']} after (stored: {stored_metrics.get('mae')} over "
                f"{stored_metrics.get('mae_holdout_days')} days)")

    if metric_got_worse(results["mae"], before["mae"]):
        logger.warning(
            f"MAE WORSENED with the increment: {before['mae']} -> {results['mae']} on the same "
            f"held-out day (tolerance x{mae_tolerance()}). The increment is DISCARDED and a full "
            "retrain is done."
        )
        return None

    metrics = _metrics(storage, "incremental", results, stored_metrics["params"], model, usable,
                       INCREMENTAL_METRIC_DAYS,
                       full_trained_at=stored_metrics.get("full_trained_at"),
                       consecutive_fulls=0)
    metrics["mae_before_increment"] = before["mae"]
    model_path = settings.training().MODEL_OUTPUT_PATH
    model_key = save_model_bundle(storage, model_path, model, stored_columns, metrics)
    logger.info(f"Bundle updated as '{model_key}' (storage={type(storage).__name__})")
    return 0


def train_one_target(tenant: str, scope: str) -> int:
    """Full cycle for ONE tenant/scope: read the history, train (warm or cold),
    upload the bundle. Called inside `with fiware_target(...)`, so tenant/scope reach
    Aether and the storage key through the environment (see
    helpers/fiware_targets.py)."""
    logger.info("=" * 80)
    logger.info("CROWD MODEL TRAINING - START")
    training = settings.training()
    logger.info(f"HOLDOUT_DAYS={training.TRAINING_HOLDOUT_DAYS}")
    logger.info(settings.calendar().describe())
    logger.info("=" * 80)

    storage = get_storage()
    stored = None
    if force_full_retrain():
        logger.info("FORCE_FULL_RETRAIN=true: ignoring whatever is in storage.")
    else:
        stored = load_model_bundle(storage, training.MODEL_OUTPUT_PATH)

    if stored:
        stored_model, stored_columns, stored_metrics = stored
        retrain_due = (full_retrain_is_due(stored_metrics) or calendar_changed(stored_metrics)
                      or weather_availability_changed(stored_metrics)
                      or events_registry_changed(storage, stored_metrics))
        if not stored_metrics.get("params"):
            logger.warning("The stored model has no hyperparameters in its metrics sidecar: "
                           "full retrain (the new trees cannot be grown at random).")
        elif retrain_due:
            logger.warning(f"Full retrain DUE: {retrain_due}. Increments in a row pull the model "
                           "towards the last few days; this re-anchors it on the whole history.")
        elif not room_for_more_trees(stored_model):
            logger.warning(f"The stored model already has {n_trees(stored_model)} trees and the "
                           f"increment does not fit under MAX_ESTIMATORS={max_estimators()}: "
                           "full retrain, which is exactly what the cap is for.")
        else:
            exit_code = train_incremental(storage, stored_model, stored_columns, stored_metrics)
            if exit_code is not None:
                logger.info("=" * 80)
                logger.info("CROWD MODEL TRAINING - COMPLETED (incremental)" if exit_code == 0
                            else "CROWD MODEL TRAINING - FAILED (incremental)")
                logger.info("=" * 80)
                return exit_code

    previous_fulls = stored[2].get("consecutive_full_retrains", 0) if stored else 0
    exit_code = train_full(storage, previous_fulls=previous_fulls)
    logger.info("=" * 80)
    logger.info("CROWD MODEL TRAINING - COMPLETED (full)" if exit_code == 0
                else "CROWD MODEL TRAINING - FAILED")
    logger.info("=" * 80)
    return exit_code


def main() -> int:
    """One full cycle per FIWARE_TARGETS entry. A failing target does not abort
    the others, but it does turn the exit code red (see run_for_each_target)."""
    return run_for_each_target(
        train_one_target, logger,
        config_errors=(AetherConfigError, NoHistoryError, ValueError),
    )

