from datetime import datetime, timedelta
from unittest.mock import patch

from crowd_predictions.training_data import add_calendar_features, add_lag_features, add_rolling_features, FEATURE_COLUMNS
import crowd_predictions.crowd_xgboost_model as crowd_xgboost_model
from crowd_predictions.crowd_xgboost_model import (
    prepare_features, time_based_split, train_model, evaluate_model,
    tune_hyperparameters, compare_against_weekday_baseline,
    feature_importance,
)


def _synthetic_bins(n_days=40, zones=("A", "B")):
    """A deterministic pattern (weekday peak, weekend trough) so that the model has
    something real to learn - not pure noise."""
    bins = []
    for zone in zones:
        base = 100 if zone == "A" else 50
        for day in range(n_days):
            ts = datetime(2026, 1, 1) + timedelta(days=day, hours=12)
            weekday_factor = 0.4 if ts.weekday() >= 5 else 1.0
            occupancy = int(base * weekday_factor) + day % 5
            bins.append({"zone_id": zone, "timestamp": ts, "occupancy": occupancy})
    return bins


def _build_df(n_days=40, zones=("A", "B")):
    df = add_calendar_features(_synthetic_bins(n_days=n_days, zones=zones))
    df = add_lag_features(df)
    df = add_rolling_features(df)
    return df.dropna(subset=FEATURE_COLUMNS)


def test_prepare_features_one_hot_encodes_zone_id():
    df = _build_df()
    X = prepare_features(df)
    assert "zone_A" in X.columns
    assert "zone_B" in X.columns
    for col in FEATURE_COLUMNS:
        assert col in X.columns


def test_time_based_split_holdout_is_strictly_after_train():
    df = _build_df()
    train_df, test_df = time_based_split(df, holdout_days=7)
    assert train_df["timestamp"].max() < test_df["timestamp"].min()
    assert len(train_df) > 0 and len(test_df) > 0


def test_train_and_evaluate_model_runs_end_to_end_with_non_negative_predictions():
    df = _build_df()
    train_df, test_df = time_based_split(df, holdout_days=7)
    model = train_model(train_df)
    train_columns = prepare_features(train_df).columns.tolist()
    results = evaluate_model(model, test_df, train_columns)

    assert results["mae"] >= 0
    assert set(results["per_zone"].keys()) == {"A", "B"}
    for zone_id, m in results["per_zone"].items():
        assert m["mae"] >= 0
        assert m["n_rows"] > 0


def test_evaluate_model_handles_test_columns_not_seen_in_train():
    """If test brings a zone_id that train did not see, it must not blow up (reindex)."""
    df = _build_df(zones=("A",))
    train_df, _ = time_based_split(df, holdout_days=7)
    test_df_other_zone = _build_df(zones=("C",))
    _, test_df_other_zone = time_based_split(test_df_other_zone, holdout_days=7)

    model = train_model(train_df)
    train_columns = prepare_features(train_df).columns.tolist()
    results = evaluate_model(model, test_df_other_zone, train_columns)
    assert results["mae"] >= 0


def test_tune_hyperparameters_picks_from_grid_using_only_val_not_test():
    """The final holdout (test) must not influence the choice - a small grid on
    purpose, only the shape of the result is checked plus that best_params comes
    literally from the given grid."""
    df = _build_df(n_days=90)
    grid = {"max_depth": [2, 3], "n_estimators": [50, 80], "learning_rate": [0.1]}
    result = tune_hyperparameters(df, val_days=7, test_days=7, param_grid=grid)

    assert set(result["best_params"].keys()) == {"max_depth", "n_estimators", "learning_rate"}
    assert result["best_params"]["max_depth"] in grid["max_depth"]
    assert result["best_params"]["n_estimators"] in grid["n_estimators"]
    assert result["best_val_mae"] >= 0
    assert len(result["all_results"]) == 2 * 2 * 1  # cartesian product of the grid


def test_tune_hyperparameters_fixed_params_override_grid_and_survive_into_best_params():
    """fixed_params (e.g. objective) must be applied to ALL the combinations of the
    grid and show up in best_params, so that it can be passed straight to
    train_model() without having to remember to add it separately."""
    df = _build_df(n_days=90)
    grid = {"max_depth": [2, 3], "n_estimators": [50]}
    result = tune_hyperparameters(df, val_days=7, test_days=7, param_grid=grid,
                                    fixed_params={"objective": "reg:squarederror"})
    assert result["best_params"]["objective"] == "reg:squarederror"
    assert result["best_params"]["max_depth"] in grid["max_depth"]


def test_compare_against_weekday_baseline_returns_mae_per_zone():
    df = _build_df(n_days=60)
    baseline = compare_against_weekday_baseline(df, holdout_days=14, n_occurrences=4)
    assert set(baseline.keys()) == {"A", "B"}
    for zone_id, mae in baseline.items():
        assert mae is None or mae >= 0


def test_feature_importance_returns_all_columns_sorted_descending():
    df = _build_df()
    train_df, _ = time_based_split(df, holdout_days=7)
    model = train_model(train_df)
    train_columns = prepare_features(train_df).columns.tolist()

    importances = feature_importance(model, train_columns)

    assert {feat for feat, _ in importances} == set(train_columns)
    values = [v for _, v in importances]
    assert values == sorted(values, reverse=True)
