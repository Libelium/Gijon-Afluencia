import shutil
import tempfile
from datetime import datetime, timedelta

from crowd_predictions.training_data import (add_calendar_features, add_lag_features, add_rolling_features,
                            select_feature_columns, FEATURE_COLUMNS)
from crowd_predictions.crowd_xgboost_model import prepare_features, train_model
from crowd_predictions.etl.predict.transform import (PredictTransform, _default_start_ts, _hour_aligned_now,
                                    _prediction_entity_id)


def _history(zone_id="X", n_days=40, base=10):
    return [{"zone_id": zone_id, "timestamp": datetime(2026, 1, 1) + timedelta(days=d, hours=12), "occupancy": base + d}
            for d in range(n_days)]


def _history_hourly(zone_id="X", n_days=40, base=10):
    """One bin EVERY HOUR of every day - needed to test horizons >24h."""
    return [
        {"zone_id": zone_id, "timestamp": datetime(2026, 1, 1) + timedelta(days=d, hours=h), "occupancy": base + d}
        for d in range(n_days) for h in range(24)
    ]


def _train_tiny_model(history):
    df = add_calendar_features(history)
    df = add_lag_features(df)
    df = add_rolling_features(df)
    df = df.dropna(subset=FEATURE_COLUMNS)
    model = train_model(df, params={"n_estimators": 10, "max_depth": 2})
    return model, prepare_features(df).columns.tolist()


def test_prediction_entity_id_with_a_short_zone_id():
    """A bare id ("CROWD01", not a URN) is left as-is - unchanged behaviour."""
    assert _prediction_entity_id("CROWD01") == "urn:ngsi-ld:CrowdFlowPrediction:CROWD01_pred"


def test_prediction_entity_id_does_not_double_prefix_a_source_urn():
    """zone_id is a full URN (CrowdFlowZone's own). Interpolating it straight in produced
    "urn:ngsi-ld:CrowdFlowPrediction:urn:ngsi-ld:CrowdFlowObserved:Device_1_pred",
    whose type no longer matched the one helpers/uploader.py derives from the URN."""
    assert _prediction_entity_id("urn:ngsi-ld:CrowdFlowObserved:Device_1") == \
        "urn:ngsi-ld:CrowdFlowPrediction:Device_1_pred"


def test_default_start_ts_anchors_right_after_freshest_data_not_wall_clock():
    """Found while testing against a real multi-month history: if it lags behind
    "now" (a one-off export, ingestion with lag), anchoring to wall-clock means
    lag_1d/1w find nothing and EVERY prediction gets discarded."""
    stale_history = [{"zone_id": "X", "timestamp": datetime(2020, 1, 1, 12, 0), "occupancy": 5}]
    start = _default_start_ts(stale_history, bin_minutes=60)
    assert start == datetime(2020, 1, 1, 13, 0)  # right after the last data point, not "now"


def test_default_start_ts_never_goes_past_the_hour_after_the_current_one():
    """The ceiling is now + 1 bin, not "now": with an ingestion as fresh as the clock
    the last real bin IS the current hour, and starting there predicts an hour that
    already has a real measurement (it has been seen arriving duplicated)."""
    far_future_history = [{"zone_id": "X", "timestamp": datetime(2099, 1, 1, 12, 0), "occupancy": 5}]
    start = _default_start_ts(far_future_history, bin_minutes=60)
    assert start == _hour_aligned_now() + timedelta(hours=1)

    fresh_history = [{"zone_id": "X", "timestamp": _hour_aligned_now(), "occupancy": 5}]
    assert _default_start_ts(fresh_history, bin_minutes=60) == _hour_aligned_now() + timedelta(hours=1)


def test_predict_transform_csv_has_expected_columns_and_stable_pred_suffixed_urn():
    tmp_dir = tempfile.mkdtemp()
    try:
        history = _history()
        model, train_columns = _train_tiny_model(history)
        start = datetime(2026, 2, 10, 12, 0)

        transformer = PredictTransform(history_bins=history, model=model, train_columns=train_columns,
                                         horizon_hours=1, start_ts=start, output_dir=tmp_dir)
        transformer.transform()

        import pandas as pd
        row = pd.read_csv(transformer.exported_files[0]).iloc[0]
        # Stable ID with the _pred suffix, with NO
        # embedded timestamp - it is the same id on every run, it is updated, not recreated.
        assert row["urn"] == "urn:ngsi-ld:CrowdFlowPrediction:X_pred"
        assert row["zoneId"] == "X"
        assert row["predictedOccupancy"] >= 0
    finally:
        shutil.rmtree(tmp_dir)


def test_predict_transform_goes_beyond_24h_in_one_entity_not_one_per_hour():
    """Two things at once, because both need the same expensive 48h recursive run:

    - the horizon is reached: with a dense history the ONE CSV carries all 48 rows.
      Before predict_recursive the version without feedback stopped at 24 (see
      test_prediction_features), and every row carries horizonStep;
    - the entity count does NOT follow the horizon: 1 zone is 1 file whether the
      horizon is 1 or 48. It used to generate 48 files/entities.
    """
    tmp_dir = tempfile.mkdtemp()
    try:
        history = _history_hourly()
        model, train_columns = _train_tiny_model(_history())  # trained with the usual history, it just needs to exist
        start = datetime(2026, 2, 10, 0, 0)  # right after the last day of the dense history

        transformer = PredictTransform(history_bins=history, model=model, train_columns=train_columns,
                                         horizon_hours=48, start_ts=start, output_dir=tmp_dir)
        ok = transformer.transform()

        assert ok is True
        assert len(transformer.exported_files) == 1
        assert transformer.exported_files[0].endswith("urn:ngsi-ld:CrowdFlowPrediction:X_pred.csv")

        import pandas as pd
        df = pd.read_csv(transformer.exported_files[0])
        assert len(df) == 48
        assert sorted(df["horizonStep"]) == list(range(1, 49))
        assert (df["urn"] == "urn:ngsi-ld:CrowdFlowPrediction:X_pred").all()  # same entity in every row
    finally:
        shutil.rmtree(tmp_dir)


def test_predict_transform_one_file_per_zone_with_multiple_zones():
    tmp_dir = tempfile.mkdtemp()
    try:
        history = _history(zone_id="A") + _history(zone_id="B")
        model, train_columns = _train_tiny_model(_history(zone_id="A") + _history(zone_id="B"))
        start = datetime(2026, 2, 10, 12, 0)

        transformer = PredictTransform(history_bins=history, model=model, train_columns=train_columns,
                                         horizon_hours=1, start_ts=start, output_dir=tmp_dir)
        ok = transformer.transform()

        assert ok is True
        assert len(transformer.exported_files) == 2  # 2 zones -> 2 files, none mixed together
        urns = {p.rsplit("/", 1)[-1] for p in transformer.exported_files}
        assert urns == {"urn:ngsi-ld:CrowdFlowPrediction:A_pred.csv", "urn:ngsi-ld:CrowdFlowPrediction:B_pred.csv"}
    finally:
        shutil.rmtree(tmp_dir)


def test_a_model_trained_without_the_28_day_features_still_predicts(caplog):
    """End to end on the prediction side: with 15 days of history the model is
    trained WITHOUT rolling_*_28d, and the .columns.json sidecar is what makes it
    predict - demanding the 15 constant features would discard every row (with 15
    days of history rolling_*_28d is NaN, by design). Verified, not assumed."""
    tmp_dir = tempfile.mkdtemp()
    try:
        history = _history_hourly(n_days=15)
        df = add_calendar_features(history)
        df = add_lag_features(df)
        df = add_rolling_features(df)
        feature_columns = select_feature_columns(df)
        assert "rolling_mean_28d" not in feature_columns  # the premise of the test

        model = train_model(df.dropna(subset=feature_columns), params={"n_estimators": 10, "max_depth": 2},
                            feature_columns=feature_columns)
        train_columns = prepare_features(df.dropna(subset=feature_columns), feature_columns).columns.tolist()

        transformer = PredictTransform(history_bins=history, model=model, train_columns=train_columns,
                                         horizon_hours=6, start_ts=datetime(2026, 1, 16, 0, 0),
                                         output_dir=tmp_dir)
        assert transformer.transform() is True

        import pandas as pd
        rows = pd.read_csv(transformer.exported_files[0])
        assert len(rows) == 6  # not a single slot discarded
        assert (rows["predictedOccupancy"] >= 0).all()
        # And it does NOT ask for what the model never saw.
        assert transformer.feature_columns == feature_columns
    finally:
        shutil.rmtree(tmp_dir)


def test_predict_transform_fails_cleanly_when_nothing_is_predictable():
    tmp_dir = tempfile.mkdtemp()
    try:
        history = [{"zone_id": "X", "timestamp": datetime(2026, 1, 1, 12, 0), "occupancy": 5}]  # 1 day, insufficient
        model, train_columns = _train_tiny_model(_history())  # a model from another history, it just needs to exist
        start = datetime(2026, 1, 2, 12, 0)

        transformer = PredictTransform(history_bins=history, model=model, train_columns=train_columns,
                                         horizon_hours=1, start_ts=start, output_dir=tmp_dir)
        ok = transformer.transform()

        assert ok is False
        assert transformer.exported_files == []
    finally:
        shutil.rmtree(tmp_dir)



def test_a_new_zone_without_enough_history_is_not_published_and_is_named(caplog):
    """The dangerous outcome (a plausible number computed with the features at NaN)
    is already prevented - every slot of that zone is dropped. What this adds is
    that it stops being silent: the platform shows one entity fewer and the log has
    to say which zone and what it is missing."""
    old = _history_hourly("OLD", n_days=40, base=10)
    new = [{"zone_id": "NEW", "timestamp": datetime(2026, 1, 1) + timedelta(days=d, hours=h),
            "occupancy": 5}
           for d in range(38, 40) for h in range(24)]          # only 2 days
    model, train_columns = _train_tiny_model(old)

    transform = PredictTransform(old + new, model, train_columns,
                                  horizon_hours=3, output_dir=tempfile.mkdtemp())
    with caplog.at_level("WARNING"):
        assert transform.transform() is True

    published = set(transform.predictions_df["zone_id"])
    assert published == {"OLD"}, "the zone without a window must not reach the output"
    assert "NOT PUBLISHED - NEW" in caplog.text
    # WITH quotes: it has to match the computed list, not the static sentence that
    # always mentions lag_1w ("needs 7 days of history for lag_1w/..."). Without them
    # the assert survived emptying the `missing` list entirely.
    assert "'lag_1w'" in caplog.text
    assert "NOT PUBLISHED - OLD" not in caplog.text


def test_the_dropped_records_carry_which_features_are_missing():
    """Without `missing` the log can only say "something is incomplete", which does
    not distinguish a zone needing 7 days from one needing 28."""
    from crowd_predictions.prediction_features import build_prediction_feature_table

    history = [{"zone_id": "X", "timestamp": datetime(2026, 1, 1, 12, 0), "occupancy": 5}]
    df = build_prediction_feature_table(history, ["X"], datetime(2026, 1, 2, 12, 0), horizon_hours=1)

    assert len(df.attrs["dropped"]) == 1
    missing = df.attrs["dropped"][0]["missing"]
    assert "lag_1w" in missing and "rolling_mean_28d" in missing
    # The calendar features ARE computable with a single day - they must not be listed.
    assert "hour_sin" not in missing and "is_weekend" not in missing


def test_a_published_zone_with_a_few_missing_slots_is_reported_separately(caplog):
    """Losing some hours is not the same as not existing in the output: they must
    not be logged the same way, or the important line drowns."""
    history = _history_hourly("OLD", n_days=40, base=10)
    model, train_columns = _train_tiny_model(history)

    # The last real bin is 2026-02-09 23:00, so the future slots are 02-10 00:00 and
    # 01:00. Removing the bin exactly 1 day before the SECOND one leaves its lag_1d
    # uncomputable: one slot is predicted, the other is dropped.
    history = [b for b in history if b["timestamp"] != datetime(2026, 2, 9, 1, 0)]
    transform = PredictTransform(history, model, train_columns,
                                  horizon_hours=2, output_dir=tempfile.mkdtemp())
    with caplog.at_level("WARNING"):
        transform.transform()

    assert "Slots skipped" in caplog.text
    assert "{'OLD': 1}" in caplog.text
    # It IS published, so it must not be reported as missing.
    assert "NOT PUBLISHED" not in caplog.text
