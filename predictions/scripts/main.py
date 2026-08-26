#!/usr/bin/env python3
"""
Entry point of the crowd ETL (extract -> transform -> load), same pattern as
the reference ETL's main.py. One CMD over the SAME image as the other entry
points (see README):

    python scripts/main.py

Unlike train.py/predict.py/run_daily.py it does NOT iterate FIWARE_TARGETS: it runs
once, for the single FIWARE_TENANT/FIWARE_SCOPE.
"""

import logging

from crowd_predictions.etl.crowd.etl import CrowdETL

logging.basicConfig(level=logging.INFO, format="%(message)s")


def main():
    etl = CrowdETL()
    exit_code = etl.execute_once()
    if exit_code == 0:
        print("OK - crowd ETL executed successfully")
    else:
        print("ERROR - the crowd ETL failed, see the logs above")
    raise SystemExit(0 if exit_code == 0 else 1)


if __name__ == "__main__":
    main()
