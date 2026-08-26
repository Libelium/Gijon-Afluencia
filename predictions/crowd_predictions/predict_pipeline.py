"""
Prediction pipeline: one full cycle per FIWARE_TARGETS entry.

It does NOT train. It reads the bundle train_pipeline uploaded to storage, so a
prediction run works with the model of a previous day even if today's training
failed - that resilience is the reason the two halves are separable.
"""

import logging

from crowd_predictions.etl.predict.etl import PredictETL
from crowd_predictions.helpers.aether import AetherConfigError
from crowd_predictions.helpers.aether_history import NoHistoryError
from crowd_predictions.helpers.fiware_targets import run_for_each_target

logger = logging.getLogger(__name__)

# A configuration/data problem is one clear line, not a traceback buried in the
# CronJob log. Same three as the training pipeline.
CONFIG_ERRORS = (AetherConfigError, NoHistoryError, ValueError)


def predict_one_target(tenant: str, scope: str) -> int:
    """Called inside `with fiware_target(...)`: PredictETL is BUILT here on purpose,
    because its output directory is derived from the active target."""
    # execute_once() returns -1, not 1, when a stage returns False.
    return 0 if PredictETL().execute_once() == 0 else 1


def main() -> int:
    return run_for_each_target(predict_one_target, logger, config_errors=CONFIG_ERRORS)
