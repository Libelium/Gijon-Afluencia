#!/usr/bin/env python3
"""
Entry point of the anomaly detection vertical, one CMD over the SAME image as
main.py / train.py / predict.py:

    python scripts/run_anomalies.py

Sweeps anomalies_detection/{tenant}/{scope}/ in storage, scores every csv waiting
there and leaves it in processed/ with an isOutlier column. An empty folder is the
normal state: it does nothing and exits green.

Thin on purpose: the cycle lives in crowd_predictions/anomaly_detection/pipeline.py.
"""

import logging
import sys

from crowd_predictions.anomaly_detection.pipeline import main

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")

if __name__ == "__main__":
    sys.exit(main())
