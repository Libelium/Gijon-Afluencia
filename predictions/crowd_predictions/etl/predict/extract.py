"""
Extraction for the PREDICTION ETL: history (same shape as train.py) plus the model
that train.py uploaded.

The window is the INCREMENTAL one, not the full year - predicting only needs
enough past to fill the lag/rolling features of the last real bin. It still
cannot go below the floor in helpers/aether_history.py.
"""

import json
import logging

import xgboost as xgb

from crowd_predictions.config import settings
from crowd_predictions.config.config import get_storage
from crowd_predictions.helpers.model_storage import model_storage_key
from crowd_predictions.helpers.aether_history import load_history_bins, resolve_zone_ids

logger = logging.getLogger(__name__)

class PredictExtract:
    def __init__(self):
        # In __init__ and not at module level, so a test can instantiate it twice
        # with different configuration in the same process.
        self.model_path = settings.prediction().MODEL_INPUT_PATH

        self.history_bins = []
        self.model = None
        self.train_columns = []
        self.metrics = {}

    def extract(self) -> bool:
        self.history_bins = self._load_history()
        self.model, self.train_columns, self.metrics = self._load_model()
        return bool(self.history_bins) and self.model is not None

    def _load_history(self) -> list:
        # Live from the platform, per zone (CrowdFlowZone). Zones come from ZONE_IDS
        # or, if it is empty, from autodiscovery in the broker.
        return load_history_bins(device_ids=resolve_zone_ids(), measure="occupancy",
                                 id_column="zone_id", incremental=True, bin_minutes=60)

    def _load_model(self):
        model_input_path = self.model_path
        local_model_path = f"/tmp/{model_input_path}"
        columns_filename = f"{model_input_path}.columns.json"
        local_columns_path = f"/tmp/{columns_filename}"

        storage = get_storage()
        # Same keys with tenant/scope that train.py uses when uploading it.
        try:
            storage.download_file(model_storage_key(model_input_path), local_model_path)
            storage.download_file(model_storage_key(columns_filename), local_columns_path)
        except Exception:
            # Expected case, not a bug here: train.py has not run for this target, or
            # it refused to train (under 7 days of history). Nothing is published.
            logger.error(f"No model in storage under '{model_storage_key(model_input_path)}' "
                         "(+.columns.json): train.py has not run for this target yet, or it "
                         "refused to train for lack of history. NOTHING is published.")
            raise

        model = xgb.XGBRegressor()
        model.load_model(local_model_path)
        with open(local_columns_path) as f:
            train_columns = json.load(f)

        # OPTIONAL, unlike the two above: it carries the prediction band, and a
        # model trained before that existed simply has none. Missing metrics must
        # not stop a perfectly good model from predicting - it publishes without
        # the band.
        metrics = {}
        metrics_filename = f"{model_input_path}.metrics.json"
        try:
            local_metrics_path = f"/tmp/{metrics_filename}"
            storage.download_file(model_storage_key(metrics_filename), local_metrics_path)
            with open(local_metrics_path) as f:
                metrics = json.load(f)
        except Exception as e:
            logger.warning(f"No metrics sidecar for '{model_input_path}' ({e}) - predicting "
                           "without a prediction band.")

        return model, train_columns, metrics
