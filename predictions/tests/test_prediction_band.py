"""
The prediction band: `predictedOccupancyLower`/`Upper` published alongside every
predicted value.

It is measured at TRAINING time (crowd_xgboost_model.backtest_spread_by_horizon_step,
stored in the model's metrics sidecar) and applied at PREDICTION time, because
predict.py has no history to measure it on and recomputing it per run would cost a
backtest every time.
"""

import os
import shutil
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch

import pandas as pd
import pytest

from crowd_predictions.crowd_xgboost_model import prepare_features, train_model
from crowd_predictions.etl.predict.transform import PredictTransform, prediction_band
from crowd_predictions.training_data import (FEATURE_COLUMNS, add_calendar_features,
                                             add_lag_features, add_rolling_features)

SPREAD = {"1": {"lo": -0.10, "hi": 0.15},
          "2": {"lo": -0.30, "hi": 0.40}}


# --- The band itself ------------------------------------------------------------

def test_the_bounds_are_relative_to_the_predicted_value():
    """Stored relative, not as a headcount: zones differ by two orders of magnitude
    in occupancy, so the same band has to scale with whatever is predicted."""
    assert prediction_band(100, 1, SPREAD) == (90, 115)
    assert prediction_band(1000, 1, SPREAD) == (900, 1150)


def test_the_band_is_asymmetric_when_the_model_is_biased_at_that_step():
    """Percentiles of the SIGNED error, so a step where the model systematically
    under-shoots does not get a band centred on a biased point estimate."""
    lower, upper = prediction_band(100, 2, {"2": {"lo": -0.10, "hi": 0.50}})
    assert (100 - lower) != (upper - 100)
    assert (lower, upper) == (90, 150)


def test_the_band_widens_with_the_horizon():
    """The quantitative version of what horizonStep says qualitatively: a value 24
    steps out leans on its own previous predictions."""
    near = prediction_band(100, 1, SPREAD)
    far = prediction_band(100, 2, SPREAD)
    assert (far[1] - far[0]) > (near[1] - near[0])


def test_a_lower_bound_never_goes_negative():
    """A negative headcount is nonsense whatever the measured error says."""
    assert prediction_band(3, 1, {"1": {"lo": -2.0, "hi": 0.5}})[0] == 0


def test_a_step_with_no_measured_band_publishes_none():
    assert prediction_band(100, 99, SPREAD) == (None, None)
    assert prediction_band(100, 1, {}) == (None, None)
    assert prediction_band(100, 1, None) == (None, None)


def test_a_half_measured_step_is_treated_as_no_band():
    """Both bounds or neither - publishing one alone would read as a hard limit."""
    assert prediction_band(100, 1, {"1": {"lo": -0.1}}) == (None, None)


# --- Published alongside the prediction -------------------------------------------

def _history(days=40, zone="urn:ngsi-ld:CrowdFlowZone:Z01"):
    start = datetime(2026, 1, 1)
    return [{"zone_id": zone, "timestamp": start + timedelta(hours=h),
             "occupancy": 40 + (h % 24) * 2}
            for h in range(days * 24)]


def _tiny_model(bins):
    """Same shape as tests/test_predict_etl.py's own helper: train_model takes the
    whole frame, not X/y."""
    df = add_rolling_features(add_lag_features(add_calendar_features(bins)))
    df = df.dropna(subset=FEATURE_COLUMNS)
    model = train_model(df, params={"n_estimators": 10, "max_depth": 2})
    return model, prepare_features(df).columns.tolist()


@pytest.fixture
def _predict(tmp_path):
    bins = _history()
    model, train_columns = _tiny_model(bins)

    def run(metrics):
        out = tempfile.mkdtemp(dir=str(tmp_path))
        transformer = PredictTransform(history_bins=bins, model=model,
                                        train_columns=train_columns, metrics=metrics,
                                        horizon_hours=3, output_dir=out)
        assert transformer.transform() is True
        return pd.read_csv(transformer.exported_files[0])
    return run


def test_the_bounds_are_published_next_to_the_prediction(_predict):
    out = _predict({"spread_by_horizon_step": SPREAD})
    assert {"predictedOccupancyLower", "predictedOccupancyUpper"} <= set(out.columns)

    row = out[out.horizonStep == 1].iloc[0]
    assert row.predictedOccupancyLower <= row.predictedOccupancy <= row.predictedOccupancyUpper


def test_each_hour_gets_the_band_of_its_own_horizon_step(_predict):
    out = _predict({"spread_by_horizon_step": SPREAD})
    step1 = out[out.horizonStep == 1].iloc[0]
    step2 = out[out.horizonStep == 2].iloc[0]

    width1 = step1.predictedOccupancyUpper - step1.predictedOccupancyLower
    width2 = step2.predictedOccupancyUpper - step2.predictedOccupancyLower
    assert width2 > width1


def test_a_model_trained_before_the_band_existed_still_predicts(_predict):
    """The metrics sidecar is OPTIONAL on the prediction side: an old bundle carries
    no band, and that must not stop it from publishing the point estimate."""
    out = _predict({})
    assert "predictedOccupancy" in out.columns
    assert "predictedOccupancyLower" not in out.columns


def test_no_metrics_at_all_behaves_the_same(_predict):
    out = _predict(None)
    assert not out.empty
    assert "predictedOccupancyLower" not in out.columns


# --- The read side of the sidecar --------------------------------------------------

def test_the_prediction_extract_tolerates_a_missing_metrics_sidecar(tmp_path):
    """Model and columns are required; metrics are not. A bundle without them
    predicts without a band instead of failing."""
    from crowd_predictions.etl.predict.extract import PredictExtract

    class _NoMetricsStorage:
        """Serves the model and its columns, 404s on the metrics sidecar."""

        def __init__(self, model_path, columns_path):
            self.model_path, self.columns_path = model_path, columns_path

        def download_file(self, key, path):
            if key.endswith(".metrics.json"):
                raise FileNotFoundError(key)
            source = self.columns_path if key.endswith(".columns.json") else self.model_path
            shutil.copy(source, path)
            return path

    bins = _history()
    model, train_columns = _tiny_model(bins)
    model_path = os.path.join(str(tmp_path), "m.json")
    columns_path = os.path.join(str(tmp_path), "c.json")
    model.save_model(model_path)
    pd.Series(train_columns).to_json(columns_path, orient="values")

    extract = PredictExtract()
    with patch("crowd_predictions.etl.predict.extract.get_storage",
               return_value=_NoMetricsStorage(model_path, columns_path)):
        _model, columns, metrics = extract._load_model()
    assert columns == train_columns
    assert metrics == {}
