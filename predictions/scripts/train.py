#!/usr/bin/env python3
"""
Entry point for training the crowd model. A different CMD over the SAME image as
main.py (fusion ETL) and predict.py:

    python scripts/train.py

Thin on purpose: everything it does lives in crowd_predictions/train_pipeline.py,
which is where the modes, the feature selection and the guards are documented.
"""

import logging

from crowd_predictions.helpers.aether import AetherConfigError
from crowd_predictions.helpers.aether_history import NoHistoryError
from crowd_predictions.train_pipeline import main

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AetherConfigError, NoHistoryError, ValueError) as e:
        # A single clear line instead of a traceback: these three are always
        # "somebody has to fix the configuration or ingest data", never a bug
        # here, and in a CronJob the traceback only buries the real message.
        logger.error(f"ERROR: {e}")
        raise SystemExit(1)
