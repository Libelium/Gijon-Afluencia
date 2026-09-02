"""
XGBoost model for crowd prediction (Phase 5), trained per ZONE against the live
CrowdFlowZone history (the already-fused LIDAR+SmartSpot occupancy - see
helpers/aether_history.py + training_data.py).

Design decisions (the reasoning behind each one is in the README):
  - Objective "count:poisson", not squared error - the target (occupancy) is a
    count, never negative, and Poisson is the loss function meant for that in
    XGBoost.
  - TEMPORAL split (not random) for validation: the last N days are set aside as
    test, the model never sees them during training - shuffling rows of a time
    series randomly would leak information from the future into the past (data
    leakage), and would give an optimistic and false validation metric.
  - ONE combined model for every zone (zone_id as a one-hot feature), not one
    model per zone - with a limited number of rows/zone, training separately
    wastes shared patterns (e.g. the day-of-week effect is similar across all the
    squares) that a joint model can learn.
  - MODEST hyperparameters (few trees, low depth) on purpose: with 6 months of
    history the risk of overfitting is real. No exhaustive search (Optuna) - that
    only pays off with more history.
  - It is ALWAYS compared against the already existing baseline (crowd_prediction.py,
    average per day of the week) over the same holdout - it is not enough for
    XGBoost to "work", it has to beat the simple baseline to justify the added
    complexity.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from itertools import product

import numpy as np
import pandas as pd
import xgboost as xgb

from crowd_predictions.training_data import FEATURE_COLUMNS, TARGET_COLUMN
from crowd_predictions.crowd_prediction import (DEFAULT_N_OCCURRENCES,
                                                backtest_weekday_prediction)
from crowd_predictions.helpers.aether_history import ROLLING_WARMUP_DAYS
from crowd_predictions.prediction_features import predict_recursive

DEFAULT_PARAMS = {
    "objective": "count:poisson",
    "n_estimators": 150,
    "max_depth": 4,
    "learning_rate": 0.08,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_lambda": 1.0,
    "random_state": 42,
}


def prepare_features(df: pd.DataFrame, feature_columns: list = None) -> pd.DataFrame:
    """`feature_columns` (default FEATURE_COLUMNS) + zone_id one-hot - one
    combined model for every zone, the identity of the zone goes in as a
    feature, not as a split.

    The set is a PARAMETER because it depends on the available history: a
    model trained without rolling_*_28d must be fed exactly the columns it saw."""
    zone_dummies = pd.get_dummies(df["zone_id"], prefix="zone")
    return pd.concat([df[feature_columns or FEATURE_COLUMNS], zone_dummies], axis=1)


def time_based_split(df: pd.DataFrame, holdout_days: int = 14) -> tuple:
    """
    Sets aside the last `holdout_days` (by timestamp, NOT by random row) as test -
    the model trains only with the past relative to the holdout, just as it would
    happen in production (it is never trained with data from the future).
    """
    cutoff = df["timestamp"].max() - timedelta(days=holdout_days)
    train_df = df[df["timestamp"] < cutoff].copy()
    test_df = df[df["timestamp"] >= cutoff].copy()
    return train_df, test_df


def train_model(train_df: pd.DataFrame, params: dict = None, feature_columns: list = None,
                eval_df: pd.DataFrame = None,
                early_stopping_rounds: int = None) -> xgb.XGBRegressor:
    """
    `eval_df` + `early_stopping_rounds` stop adding trees once the error on eval stops
    improving, instead of always laying down the full `n_estimators`.

    ⚠️ `eval_df` must NOT be the holdout the final metric is reported on. Choosing the
    number of trees on it makes that metric optimistic - the same leak this module
    already avoids in tune_hyperparameters() by keeping val separate from test. The
    caller carves eval out of its TRAIN slice (see train_pipeline.train_full).

    Without both arguments this behaves exactly as before: one fit, no eval set.
    """
    params = {**DEFAULT_PARAMS, **(params or {})}
    X = prepare_features(train_df, feature_columns)
    y = train_df[TARGET_COLUMN]

    if eval_df is None or not early_stopping_rounds or eval_df.empty:
        model = xgb.XGBRegressor(**params)
        model.fit(X, y)
        return model

    # The eval matrix has to carry EXACTLY the training columns, in the same order:
    # a device present in train and absent from eval would shift every column.
    X_eval = prepare_features(eval_df, feature_columns).reindex(columns=X.columns, fill_value=0)
    model = xgb.XGBRegressor(**params, early_stopping_rounds=early_stopping_rounds)
    model.fit(X, y, eval_set=[(X_eval, eval_df[TARGET_COLUMN])], verbose=False)
    return model


def evaluate_model(model: xgb.XGBRegressor, test_df: pd.DataFrame, train_columns: list,
                   feature_columns: list = None) -> dict:
    """
    Global MAE/MAPE and per zone_id. `train_columns` = the EXACT columns
    (including the zone_id dummies) that the model saw during training - test
    may not have all the same categories present, so they have to be aligned.
    """
    X_test = prepare_features(test_df, feature_columns).reindex(columns=train_columns, fill_value=0)
    y_true = test_df[TARGET_COLUMN].values
    y_pred = model.predict(X_test)
    y_pred = np.clip(y_pred, 0, None)  # never a negative occupancy

    mae = float(np.mean(np.abs(y_true - y_pred)))
    nonzero = y_true > 0
    mape = float(np.mean(np.abs(y_true[nonzero] - y_pred[nonzero]) / y_true[nonzero]) * 100) if nonzero.any() else None

    per_zone = {}
    for zone_id in test_df["zone_id"].unique():
        mask = (test_df["zone_id"] == zone_id).values
        d_true, d_pred = y_true[mask], y_pred[mask]
        d_nonzero = d_true > 0
        per_zone[zone_id] = {
            "mae": round(float(np.mean(np.abs(d_true - d_pred))), 1),
            "mape_pct": round(float(np.mean(np.abs(d_true[d_nonzero] - d_pred[d_nonzero]) / d_true[d_nonzero]) * 100), 1)
            if d_nonzero.any() else None,
            "n_rows": int(mask.sum()),
        }

    return {"mae": round(mae, 1), "mape_pct": round(mape, 1) if mape is not None else None, "per_zone": per_zone}


def tune_hyperparameters(df: pd.DataFrame, val_days: int = 14, test_days: int = 14,
                          param_grid: dict = None, fixed_params: dict = None,
                          feature_columns: list = None) -> dict:
    """
    A SMALL grid search (on purpose, see the module docstring - risk of
    overfitting with the current history, this is not an exhaustive Optuna-style
    search) with validation kept separate from the final holdout:

      - test (the last `test_days`): NEVER touched here, not even to pick
        hyperparameters - if it were used, the final metric reported would be
        optimistic (the model would have "seen" that period indirectly, by
        picking the parameters that happened to suit it best).
      - val (`val_days` immediately BEFORE test): here every combination is
        indeed tried, and the one with the lowest MAE on val is chosen.

    `fixed_params` (e.g. {"objective": "reg:squarederror"}) is applied to ALL the
    combinations of the grid, and is returned inside `best_params` - so that
    different objectives can be compared on equal terms without the
    grid itself favouring one or the other.

    Returns {"best_params", "best_val_mae", "all_results"} - all_results so that
    it can be inspected that it was not a winner by a hair/by noise.
    """
    param_grid = param_grid or {
        "max_depth": [3, 4, 5],
        "n_estimators": [100, 150, 250],
        "learning_rate": [0.05, 0.08, 0.12],
    }
    fixed_params = fixed_params or {}
    df_no_test, _test_df = time_based_split(df, holdout_days=test_days)
    tune_train_df, val_df = time_based_split(df_no_test, holdout_days=val_days)

    keys = list(param_grid.keys())
    combos = product(*param_grid.values())
    train_columns = prepare_features(tune_train_df, feature_columns).columns.tolist()

    results = []
    best = None
    for combo in combos:
        params = {**fixed_params, **dict(zip(keys, combo))}
        model = train_model(tune_train_df, params=params, feature_columns=feature_columns)
        val_result = evaluate_model(model, val_df, train_columns, feature_columns)
        row = {**params, "val_mae": val_result["mae"]}
        results.append(row)
        if best is None or row["val_mae"] < best["val_mae"]:
            best = row

    return {
        "best_params": {**fixed_params, **{k: best[k] for k in keys}},
        "best_val_mae": best["val_mae"],
        "all_results": results,
    }


def _baseline_mae_by_zone(history: list, test_df: pd.DataFrame,
                          n_occurrences: int = DEFAULT_N_OCCURRENCES) -> dict:
    """
    MAE of the baseline (crowd_prediction.backtest_weekday_prediction, average per
    day of the week) for each zone_id present in `test_df`, using `history`
    (which may be MORE history than there is in test_df - e.g. only what comes
    before a specific window) to compute the average. Factored out of
    compare_against_weekday_baseline() so it can also be reused in
    an arbitrary window, not just "the last N days".
    """
    results_by_zone = {}
    for zone_id in test_df["zone_id"].unique():
        dates = sorted({ts.date() for ts in test_df.loc[test_df["zone_id"] == zone_id, "timestamp"]})
        maes = []
        for d in dates:
            target = pd.Timestamp(d).to_pydatetime().replace(hour=12)
            result = backtest_weekday_prediction(history, zone_id, target, n_occurrences=n_occurrences)
            if result["mae"] is not None:
                maes.append(result["mae"])
        results_by_zone[zone_id] = round(sum(maes) / len(maes), 1) if maes else None
    return results_by_zone


def compare_against_weekday_baseline(df: pd.DataFrame, holdout_days: int = 14, n_occurrences: int = 8) -> dict:
    """
    Backtest of the baseline over THE SAME holdout period as XGBoost (the last
    `holdout_days`), so that the comparison is fair. Returns the average MAE of
    the baseline per zone_id.
    """
    history = [{"zone_id": row.zone_id, "timestamp": row.timestamp, "occupancy": row.occupancy}
               for row in df.itertuples(index=False)]
    _, test_df = time_based_split(df, holdout_days=holdout_days)
    return _baseline_mae_by_zone(history, test_df, n_occurrences=n_occurrences)


def feature_importance(model: xgb.XGBRegressor, train_columns: list) -> list:
    """
    [(feature, importance)] sorted descending - to know whether the model really
    learns a calendar/day-of-week pattern or whether in practice it is just
    copying lag_1d (autoregression dressed up as "XGBoost"), and to be able to
    explain it with data instead of by eye.
    """
    pairs = list(zip(train_columns, model.feature_importances_))
    return sorted(pairs, key=lambda pair: pair[1], reverse=True)


# Lookback the features need behind the backtest window: the rolling warm-up plus a
# couple of days of slack, DERIVED so the two cannot drift. Bounding it matters -
# predict_recursive rebuilds the whole feature table once PER STEP, so handing it a
# year of history makes a 24-step backtest cost minutes instead of seconds.
BACKTEST_LOOKBACK_DAYS = ROLLING_WARMUP_DAYS + 2


def _make_predict_fn(model, train_columns: list, columns: list):
    """The recursive-backtest prediction closure shared by both horizon-step backtests:
    align each feature frame to the EXACT training columns (a zone absent from a window
    would otherwise shift every column) and clamp to a non-negative rounded count."""

    def predict_fn(feature_df):
        X = prepare_features(feature_df, columns).reindex(columns=train_columns, fill_value=0)
        return [max(0, round(float(v))) for v in model.predict(X)]

    return predict_fn


def _iter_backtest_windows(bins: list, horizon_hours: int, columns: list, predict_fn,
                           n_windows: int):
    """Yield ``(predicted, truth)`` for each of ``n_windows`` non-overlapping holdouts
    going backwards from the latest bin, reusing the same trained model (only which slice
    of history is held out changes). Windows with no usable history/ground truth, or that
    predict nothing, are skipped.

    This is the recursive mechanism that backtest_by_horizon_step() (a single window) and
    backtest_spread_by_horizon_step() (several) share - see their docstrings for why this
    number does not exist anywhere else. For a single window the truth slice
    ``cutoff <= t < cutoff + horizon_hours`` is exactly ``t >= cutoff``, since no bin is
    later than the latest one the window starts from.
    """
    latest = max(b["timestamp"] for b in bins)
    for w in range(n_windows):
        cutoff = latest - timedelta(hours=horizon_hours - 1 + horizon_hours * w)
        window_end = cutoff + timedelta(hours=horizon_hours)
        lookback_start = cutoff - timedelta(days=BACKTEST_LOOKBACK_DAYS)

        history = [b for b in bins if lookback_start <= b["timestamp"] < cutoff]
        truth = {(b["zone_id"], b["timestamp"]): b["occupancy"]
                 for b in bins if cutoff <= b["timestamp"] < window_end}
        if not history or not truth:
            continue

        zone_ids = sorted({b["zone_id"] for b in history})
        predicted = predict_recursive(history, zone_ids, predict_fn, cutoff,
                                       horizon_hours=horizon_hours, feature_columns=columns)
        if predicted.empty:
            continue

        yield predicted, truth


def backtest_by_horizon_step(model, train_columns: list, bins: list, horizon_hours: int,
                             feature_columns: list = None) -> dict:
    """
    MAE per recursive step: {1: mae, 2: mae, ...} plus "overall".

    WHY THIS EXISTS: evaluate_model() measures ONE step, over rows whose lag/rolling come
    from real data. What gets published is up to PREDICTION_HORIZON_HOURS of recursive
    prediction, each step fed its own previous output - so the error of step 24 was never
    measured anywhere, and `horizonStep` travelled to the consumer as a qualitative
    warning with no number behind it. This is that number.

    The last `horizon_hours` of `bins` are held out as ground truth and predicted from
    the history before them, exactly as production does it.
    """
    if not bins or horizon_hours < 1:
        return {}

    columns = feature_columns or FEATURE_COLUMNS
    predict_fn = _make_predict_fn(model, train_columns, columns)

    errors = defaultdict(list)
    for predicted, truth in _iter_backtest_windows(bins, horizon_hours, columns,
                                                    predict_fn, n_windows=1):
        for row in predicted.itertuples(index=False):
            actual = truth.get((row.zone_id, row.timestamp))
            if actual is None:
                continue                  # a bin the zone never reported - not an error
            errors[int(row.horizon_step)].append(abs(actual - row.predicted_occupancy))

    # STRING keys, because this dict goes into the .metrics.json sidecar and JSON object
    # keys are always strings: with int keys the value would have one shape in memory and
    # another after a round trip through storage, and reading it back by [24] would raise.
    by_step = {str(step): round(float(np.mean(values)), 1)
               for step, values in sorted(errors.items())}
    if by_step:
        every = [e for values in errors.values() for e in values]
        by_step["overall"] = round(float(np.mean(every)), 1)
    return by_step


MIN_SPREAD_SAMPLES = 5
# Floors the denominator of the relative error (actual - predicted) / max(predicted,
# this) - a zone predicted at 1-2 people turns a routine few-person miss into a
# nonsense +600% relative error that would then poison the pooled percentile for
# EVERY zone at that step, small or large (see backtest_spread_by_horizon_step).
MIN_RELATIVE_DENOM = 5
# Final sanity clamp on the published band, AFTER the percentile: pooling relative
# error across zones of very different scale is already an
# approximation, not a rigorous per-zone distribution - without a cap, one unlucky
# window/zone combination could still publish a band wide enough to look broken in
# the UI (e.g. "hi" > +300%). Business-sensible bounds, not a statistical one.
MIN_BAND_LO, MAX_BAND_HI = -0.9, 1.5


@dataclass
class BacktestSpreadConfig:
    """Tuning knobs for backtest_spread_by_horizon_step(), bundled into one object so the
    function keeps a small signature. The defaults reproduce the previous positional
    defaults, so callers that pass neither behave exactly as before."""

    n_windows: int = 3
    lower_pct: float = 10
    upper_pct: float = 90


def backtest_spread_by_horizon_step(model, train_columns: list, bins: list, horizon_hours: int,
                                     feature_columns: list = None,
                                     config: "BacktestSpreadConfig" = None) -> dict:
    """
    {horizon_step: {"lo": x, "hi": y}} - empirical (lower_pct, upper_pct) percentiles of the
    RELATIVE backtest error ((actual - predicted) / predicted) at that step, to turn a bare
    predictedOccupancy into a real prediction band (predictedOccupancy * (1 + lo) ..
    predictedOccupancy * (1 + hi)) instead of just the qualitative "confidence" scalar
    predictions.py already publishes.

    RELATIVE, not an absolute headcount: zones can differ by two orders of magnitude in
    occupancy - pooling ABSOLUTE errors across all of them
    for more samples per step (see n_windows) would let a handful of large-zone samples set an
    absurd band width for a 20-person zone. A relative error is comparable across zones of any
    scale AND scales itself with predictedOccupancy at serving time, unlike a fixed headcount
    band would. Rows whose own predicted_occupancy is 0 are skipped (relative error undefined).

    SIGNED, not absolute like backtest_by_horizon_step()'s MAE: a step where the model
    systematically over/under-shoots gets an asymmetric band instead of a symmetric one
    centered on a biased point estimate.

    n_windows non-overlapping holdouts (not just the latest one), same trained model reused
    across all of them - a single window gives at most len(zone_ids) samples per step (~15
    with today's zones), too few to read a 10th/90th percentile off. Several windows going
    backwards from the latest real data pool more samples per step without retraining
    anything (only which slice of history gets held out changes). A step with fewer than
    MIN_SPREAD_SAMPLES pooled samples is omitted rather than returning a percentile computed
    on a handful of points.

    Same recursive mechanism as backtest_by_horizon_step() (predict_recursive from the history
    before each window's cutoff) - see that function's docstring for why this number does not
    exist anywhere else.
    """
    config = config or BacktestSpreadConfig()
    if not bins or horizon_hours < 1 or config.n_windows < 1:
        return {}

    columns = feature_columns or FEATURE_COLUMNS
    predict_fn = _make_predict_fn(model, train_columns, columns)

    errors = defaultdict(list)
    for predicted, truth in _iter_backtest_windows(bins, horizon_hours, columns,
                                                    predict_fn, n_windows=config.n_windows):
        for row in predicted.itertuples(index=False):
            actual = truth.get((row.zone_id, row.timestamp))
            if actual is None:
                continue
            denom = max(row.predicted_occupancy, MIN_RELATIVE_DENOM)
            errors[int(row.horizon_step)].append((actual - row.predicted_occupancy) / denom)

    return {
        str(step): {
            "lo": round(max(float(np.percentile(values, config.lower_pct)), MIN_BAND_LO), 2),
            "hi": round(min(float(np.percentile(values, config.upper_pct)), MAX_BAND_HI), 2),
        }
        for step, values in sorted(errors.items())
        if len(values) >= MIN_SPREAD_SAMPLES
    }
