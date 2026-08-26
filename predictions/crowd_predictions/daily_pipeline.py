"""
The DAILY cycle in one run: train and then predict, per tenant/scope. This is what
the CronJob invokes (scripts/run_daily.py); train.py and predict.py stay runnable on
their own for a manual run or a backfill.

⚠️ Training failing does NOT stop the prediction, and that is the whole point of this
module. the reference prediction ETL chains its stages with `and`
(`init_etl() and extract() and transform() and load()`, where transform trains AND
predicts), so a training failure means load never runs and nothing is published. Here
prediction reads the bundle from storage, so with a model from a previous day it can
still publish while training is red - and it should, because a stale prediction is
worth more than none.

The exit code is 1 if EITHER half failed on ANY target, so nobody mistakes "it
published with yesterday's model" for a healthy run.
"""

import logging

from crowd_predictions import training_data, weather
from crowd_predictions.helpers.fiware_targets import run_for_each_target
from crowd_predictions.predict_pipeline import CONFIG_ERRORS, predict_one_target
from crowd_predictions.train_pipeline import train_one_target

logger = logging.getLogger(__name__)


def train_then_predict(tenant: str, scope: str) -> int:
    """
    Both halves for ONE target. Called inside `with fiware_target(...)`.

    Training exceptions are caught HERE and not left to run_for_each_target: it would
    abort the target and skip the prediction, which is exactly what must not happen.
    """
    # First step, same reasoning as training below: a weather refresh failure
    # (Open-Meteo down, network hiccup) must not block train+predict for this
    # target - it just means precip_mm keeps whatever was cached before. Runs
    # inside fiware_target(tenant, scope), so the cache written is THIS
    # target's own segregated key, not a shared one.
    try:
        cache = weather.update_weather_cache()
        logger.info(f"Weather cache refreshed - {len(cache)} hours cached")
        # Invalidate this target's cached copy (training_data.py) - harmless if
        # nothing was cached yet (the common case: this IS the first read of
        # the process for this tenant/scope), but not a no-op the day this
        # process ever refreshes the same target twice.
        training_data.clear_caches()
    except Exception:
        logger.exception("Weather cache refresh failed - training/predicting with "
                         "whatever was cached before")

    try:
        train_exit = train_one_target(tenant, scope)
    except CONFIG_ERRORS as e:
        logger.error(f"TRAINING FAILED: {e}. Predicting anyway with whatever model is in storage.")
        train_exit = 1
    except Exception:
        logger.exception("TRAINING FAILED with an unexpected error. Predicting anyway with "
                         "whatever model is in storage.")
        train_exit = 1

    if train_exit != 0:
        logger.warning("Training did not succeed: the prediction below uses the PREVIOUSLY stored "
                       "model, so it is as fresh as that model is.")

    # Not in a try/except: a prediction failure IS this target failing, and
    # run_for_each_target logs it and isolates it from the other targets.
    predict_exit = predict_one_target(tenant, scope)

    return 0 if train_exit == 0 and predict_exit == 0 else 1


def main() -> int:
    return run_for_each_target(train_then_predict, logger, config_errors=CONFIG_ERRORS)
