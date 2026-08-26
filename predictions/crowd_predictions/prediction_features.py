"""
Builds the feature rows for FUTURE HOURS (not observed yet) from the same real
history that the training uses - it reuses
training_data.add_calendar_features/add_lag_features/add_rolling_features WITHOUT
touching them: "empty" rows (occupancy=None) are generated for the hours to
predict, they are joined with the real history, and the SAME usual functions are
left to compute calendar/lag/rolling - the exact-timestamp lookup they already use
finds the real values from 1 day/1 week ago with no changes, as long as the
prediction horizon is short (a few hours/days) and the loaded history covers that
window backwards with plenty to spare (>=28 days, for rolling_mean_28d).

`predict_recursive()` goes beyond that ~24h ceiling by predicting hour by hour and
feeding each prediction back as history for the next one - see its docstring for
the detail of the decreasing reliability (`horizon_step`).
"""

from datetime import timedelta

import pandas as pd

from crowd_predictions.training_data import add_calendar_features, add_lag_features, add_rolling_features, FEATURE_COLUMNS


def build_future_bins(zone_ids: list, start_ts, horizon_hours: int, bin_minutes: int = 60,
                       history_bins: list = None) -> list:
    """
    The hourly slots to predict, one per zone_id/hour, from `start_ts`
    (inclusive) up to `start_ts + horizon_hours` hours. occupancy=None - unknown,
    which is exactly what is to be predicted.

    Slots ALREADY COVERED by `history_bins` (same zone_id and timestamp) are not
    generated: there is nothing to predict where there is a real measurement, and
    emitting the slot anyway duplicates that hour - one row for the real bin and
    one for the slot, both predicted (seen in PRE: the first hour of every entity
    arrived twice, with horizonStep 1).
    """
    covered = {(b["zone_id"], b["timestamp"]) for b in (history_bins or [])}
    return [
        bin_ for bin_ in (
            {"zone_id": zone_id, "timestamp": start_ts + timedelta(minutes=bin_minutes * h),
             "occupancy": None}
            for zone_id in zone_ids
            for h in range(horizon_hours)
        )
        if (bin_["zone_id"], bin_["timestamp"]) not in covered
    ]


def build_prediction_feature_table(history_bins: list, zone_ids: list, start_ts,
                                     horizon_hours: int, bin_minutes: int = 60,
                                     feature_columns: list = None) -> pd.DataFrame:
    """
    real history + future slots -> DataFrame with the feature columns ready for
    model.predict(), ONLY of the rows of the generated slots.

    `feature_columns` = the set THE MODEL was trained with (from its .columns.json
    sidecar), not the 15 constants: demanding a rolling_*_28d that the model never
    saw would drop every predictable row.

    Future rows with no computable lag/rolling (dropna) are returned separately
    via the `.attrs["dropped"]` attribute instead of vanishing silently - the
    caller must log how many entities are left unpredicted and why.
    """
    future_bins = build_future_bins(zone_ids, start_ts, horizon_hours, bin_minutes=bin_minutes,
                                     history_bins=history_bins)
    combined = history_bins + future_bins

    df = add_calendar_features(combined)
    df = add_lag_features(df)
    df = add_rolling_features(df)

    # By the IDENTITY of the generated slots, not by `timestamp >= start_ts`: that
    # comparison also selects the history rows dated at start_ts or later (which
    # happens whenever the ingestion is as fresh as the clock), and it would predict
    # over an hour that already has a real measurement.
    slots = {(b["zone_id"], b["timestamp"]) for b in future_bins}
    future_mask = [(row.zone_id, row.timestamp) in slots
                   for row in df.itertuples(index=False)]
    future_df = df[future_mask].reset_index(drop=True)

    columns = feature_columns or FEATURE_COLUMNS
    has_all_features = future_df[columns].notna().all(axis=1)
    complete = future_df[has_all_features].reset_index(drop=True)

    # WHICH features are missing, not just that something is: it is the difference
    # between "this zone needs 7 days of history" and "it needs 28" for whoever
    # reads the log.
    complete.attrs["dropped"] = [
        {"zone_id": row["zone_id"], "timestamp": row["timestamp"],
         "missing": [c for c in columns if pd.isna(row[c])]}
        for _, row in future_df[~has_all_features].iterrows()
    ]

    return complete


def predict_recursive(history_bins: list, zone_ids: list, predict_fn, start_ts,
                        horizon_hours: int, bin_minutes: int = 60,
                        feature_columns: list = None) -> pd.DataFrame:
    """
    Predicts hour by hour, FEEDING each prediction back as if it were real history
    so that the lag/rolling of the next hour can be computed - that is how the
    ~24h ceiling of build_prediction_feature_table() is overcome (beyond that
    window, lag_1d/1w need an hour that is not real data yet).

    predict_fn: callable(feature_df) -> array of predicted values, in the SAME
    order as the rows of feature_df - it is injected (crowd_xgboost_model is not
    imported here) so that this can be tested without a real model.

    Every returned row carries `horizon_step` (1, 2, 3...) - how many recursive
    steps separate it from the last REAL data point. The error accumulates with
    each step (the prediction of step 3 depends on the one from step 2, not on
    real data), so `horizon_step` is the decreasing-reliability signal that
    whoever uses this must consume - re-running this same pipeline later replaces
    those hours with a version that has a lower horizon_step (closer to real
    data), refining itself over time.

    Real gaps (a step without enough history on SOME zone) are skipped without
    breaking the chain of the other zones - accumulated in `.attrs["dropped"]`
    of the result, the same as build_prediction_feature_table.
    """
    working_history = list(history_bins)
    steps = []
    all_dropped = []

    for step in range(1, horizon_hours + 1):
        current_ts = start_ts + timedelta(minutes=bin_minutes * (step - 1))
        feature_df = build_prediction_feature_table(working_history, zone_ids, current_ts,
                                                       horizon_hours=1, bin_minutes=bin_minutes,
                                                       feature_columns=feature_columns)
        all_dropped.extend(feature_df.attrs.get("dropped", []))
        if feature_df.empty:
            continue

        predicted_values = list(predict_fn(feature_df))
        feature_df = feature_df.copy()
        feature_df["predicted_occupancy"] = predicted_values
        feature_df["horizon_step"] = step
        steps.append(feature_df)

        for row, pred in zip(feature_df.itertuples(index=False), predicted_values):
            working_history.append({"zone_id": row.zone_id, "timestamp": row.timestamp, "occupancy": pred})

    result = pd.concat(steps, ignore_index=True) if steps else pd.DataFrame()
    result.attrs["dropped"] = all_dropped
    return result
