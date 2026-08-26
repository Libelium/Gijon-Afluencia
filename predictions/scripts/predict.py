#!/usr/bin/env python3
"""
Crowd PREDICTION entry point, one CMD over the SAME image as main.py and train.py:

    python scripts/predict.py

Requires train.py to have run at some point - it reads the model that train.py
uploads to storage, NOT one trained here. Thin on purpose: the cycle lives in
crowd_predictions/predict_pipeline.py.
"""

import logging

from crowd_predictions.predict_pipeline import main

logging.basicConfig(level=logging.INFO, format="%(message)s")


if __name__ == "__main__":
    exit_code = main()
    if exit_code == 0:
        print("OK - crowd prediction generated and published successfully")
    else:
        print("ERROR - the crowd prediction failed for at least one target, see the logs above")
    raise SystemExit(exit_code)
