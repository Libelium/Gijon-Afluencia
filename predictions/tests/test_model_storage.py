import json
import os
from unittest.mock import patch

import numpy as np
import pytest
import xgboost as xgb

from crowd_predictions.helpers.model_storage import (COLUMNS_SUFFIX, METRICS_SUFFIX, MissingSegregationError,
                                    load_model_bundle, model_storage_key, save_model_bundle)


def test_key_includes_prefix_tenant_and_scope():
    with patch.dict(os.environ, {"FIWARE_TENANT": "libelium", "FIWARE_SCOPE": "tenant_a"}):
        assert model_storage_key("crowd_xgboost_model.json") == \
            "prediction-models/libelium/tenant_a/crowd_xgboost_model.json"


def test_two_deployments_do_not_collide():
    """The reason this module exists: the flat key made two deployments over the
    same bucket overwrite each other's model with no error."""
    with patch.dict(os.environ, {"FIWARE_TENANT": "libelium", "FIWARE_SCOPE": "tenant_a"}):
        tenant_a = model_storage_key("crowd_xgboost_model.json")
    with patch.dict(os.environ, {"FIWARE_TENANT": "libelium", "FIWARE_SCOPE": "otra_ciudad"}):
        other_city = model_storage_key("crowd_xgboost_model.json")
    assert tenant_a != other_city


def test_scope_with_slashes_becomes_a_single_path_segment():
    """FIWARE uses "/" as the root scope and accepts "/a/b". Without normalizing,
    "/" would give an empty segment in the key and "/a/b" would create unexpected
    levels."""
    with patch.dict(os.environ, {"FIWARE_TENANT": "t", "FIWARE_SCOPE": "/"}):
        assert model_storage_key("m.json") == "prediction-models/t/_/m.json"

    with patch.dict(os.environ, {"FIWARE_TENANT": "t", "FIWARE_SCOPE": "/a/b/"}):
        assert model_storage_key("m.json") == "prediction-models/t/a_b/m.json"


def test_prefix_is_configurable_and_slashes_are_trimmed():
    with patch.dict(os.environ, {"MODELS_PREFIX": "/modelos/", "FIWARE_TENANT": "t",
                                  "FIWARE_SCOPE": "s"}):
        assert model_storage_key("m.json") == "modelos/t/s/m.json"


def test_an_unset_tenant_is_an_error_not_a_shared_default():
    """The old ".../default/_/" fallback put two unconfigured deployments in the same
    prefix - the collision the segregation exists to prevent. (FIWARE_SCOPE cannot be
    unset the same way: its field default is a real "/", every scope on the platform.)"""
    with patch.dict(os.environ, {"FIWARE_SCOPE": "/"}, clear=True):
        with pytest.raises(MissingSegregationError, match="FIWARE_TENANT"):
            model_storage_key("m.json")


def test_sidecar_of_columns_shares_the_same_folder():
    """predict.py downloads both from the same folder; if they diverged, it would
    find the model and not the columns."""
    with patch.dict(os.environ, {"FIWARE_TENANT": "libelium", "FIWARE_SCOPE": "tenant_a"}):
        model = model_storage_key("crowd_xgboost_model.json")
        columns = model_storage_key("crowd_xgboost_model.json.columns.json")
    assert os.path.dirname(model) == os.path.dirname(columns)


class _DictStorage:
    """The StorageType contract in memory. download_file RAISES when the key is
    missing, which is how load_model_bundle tells warm from cold."""

    def __init__(self):
        self.files = {}

    def upload_file(self, filename, path):
        with open(path, "rb") as f:
            self.files[filename] = f.read()
        return path

    def download_file(self, filename, path):
        if filename not in self.files:
            raise FileNotFoundError(filename)
        with open(path, "wb") as f:
            f.write(self.files[filename])
        return path

    def delete_file(self, path):
        self.files.pop(path, None)
        return True

    def list_all(self):
        return sorted(self.files)


def _tiny_model():
    model = xgb.XGBRegressor(n_estimators=5, max_depth=2)
    model.fit(np.zeros((10, 3)), np.arange(10))
    return model


def test_bundle_round_trips_model_columns_and_metrics(tmp_path):
    storage = _DictStorage()
    with patch.dict(os.environ, {"FIWARE_TENANT": "t", "FIWARE_SCOPE": "/"}):
        save_model_bundle(storage, "m.json", _tiny_model(), ["hour_sin", "zone_A"],
                          {"mae": 3.2, "params": {"max_depth": 2}}, local_dir=str(tmp_path))
        model, columns, metrics = load_model_bundle(storage, "m.json", local_dir=str(tmp_path))

    assert columns == ["hour_sin", "zone_A"]
    assert metrics["mae"] == 3.2
    assert model.get_booster().num_boosted_rounds() == 5


def test_no_bundle_in_storage_means_cold_start(tmp_path):
    with patch.dict(os.environ, {"FIWARE_TENANT": "t", "FIWARE_SCOPE": "/"}):
        assert load_model_bundle(_DictStorage(), "m.json", local_dir=str(tmp_path)) is None


def test_a_custom_serialize_deserialize_pair_round_trips_a_non_xgboost_object(tmp_path):
    """save_model_bundle/load_model_bundle must work for any model type, not
    only XGBoost - the anomaly detection module (a sklearn Birch + plain
    Python state) reuses this exact pair via anomaly_detection/storage.py."""
    storage = _DictStorage()
    payload = {"not": "xgboost", "numbers": [1, 2, 3]}

    def serialize(obj, path):
        with open(path, "w") as f:
            json.dump(obj, f)

    def deserialize(path):
        with open(path) as f:
            return json.load(f)

    with patch.dict(os.environ, {"FIWARE_TENANT": "t", "FIWARE_SCOPE": "/"}):
        save_model_bundle(storage, "m.pkl", payload, ["a", "b"], {"note": "custom"},
                          local_dir=str(tmp_path), serialize=serialize)
        model, columns, metrics = load_model_bundle(storage, "m.pkl", local_dir=str(tmp_path),
                                                     deserialize=deserialize)

    assert model == payload
    assert columns == ["a", "b"]
    assert metrics == {"note": "custom"}


def test_default_behaviour_is_unchanged_for_existing_xgboost_callers(tmp_path):
    """Regression guard: omitting serialize/deserialize (every existing
    caller - train_pipeline.py) must behave exactly as before this module
    gained the pluggable parameters."""
    storage = _DictStorage()
    with patch.dict(os.environ, {"FIWARE_TENANT": "libelium", "FIWARE_SCOPE": "tenant_a"}):
        save_model_bundle(storage, "m.json", _tiny_model(), ["hour_sin", "zone_A"],
                          {"mae": 3.2, "params": {"max_depth": 2}}, local_dir=str(tmp_path))
        model, columns, metrics = load_model_bundle(storage, "m.json", local_dir=str(tmp_path))

    assert columns == ["hour_sin", "zone_A"]
    assert metrics["mae"] == 3.2
    assert model.get_booster().num_boosted_rounds() == 5


def test_an_incomplete_bundle_also_means_cold_start(tmp_path):
    """A model with no metrics sidecar cannot be warm-started: there are no hyperparameters for the new trees
    and no MAE to compare against."""
    storage = _DictStorage()
    with patch.dict(os.environ, {"FIWARE_TENANT": "t", "FIWARE_SCOPE": "/"}):
        save_model_bundle(storage, "m.json", _tiny_model(), ["hour_sin"], {"mae": 1.0},
                          local_dir=str(tmp_path))
        del storage.files[model_storage_key(f"m.json{METRICS_SUFFIX}")]
        assert load_model_bundle(storage, "m.json", local_dir=str(tmp_path)) is None
        # The columns one is still there: the bundle is incomplete, not absent.
        assert model_storage_key(f"m.json{COLUMNS_SUFFIX}") in storage.files
