#!/usr/bin/env python3
"""
Manual backfill entry point for the weather cache. The daily refresh lives in
daily_pipeline.py now (first step of train_then_predict, per target) - this
script is for repopulating the cache by hand (e.g. after changing
WEATHER_LAT/LON, or right after a deployment before the first cron run):

    python scripts/update_weather.py

Thin on purpose: everything it does lives in crowd_predictions/weather.py. One
full cycle per FIWARE_TARGETS entry, same as train.py/predict.py - a
single-tenant run without FIWARE_TARGETS set still works (see
fiware_targets.parse_target_specs).
"""

import logging

from crowd_predictions.helpers.fiware_targets import run_for_each_target
from crowd_predictions.weather import refresh_weather_one_target

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    raise SystemExit(run_for_each_target(refresh_weather_one_target, logger))
