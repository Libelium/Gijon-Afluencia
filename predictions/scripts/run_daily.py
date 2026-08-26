#!/usr/bin/env python3
"""
The CronJob entry point: trains and predicts in one run, per tenant/scope.

    python scripts/run_daily.py

DAILY cadence. Not hourly: a warm start adds N_ESTIMATORS_INCREMENT trees per run,
so running it hourly burns through the tree budget in under a day and turns the
expensive full retrain (a year of history plus hyperparameter tuning, paid PER
TARGET) into a daily event.

A failure to train does not stop the prediction - see crowd_predictions/
daily_pipeline.py. Exit code 1 if either half failed on any target.
"""

import logging

from crowd_predictions.daily_pipeline import main

logging.basicConfig(level=logging.INFO, format="%(message)s")


if __name__ == "__main__":
    exit_code = main()
    if exit_code == 0:
        print("OK - trained and published for every target")
    else:
        print("ERROR - training or prediction failed for at least one target, see the logs above")
    raise SystemExit(exit_code)
