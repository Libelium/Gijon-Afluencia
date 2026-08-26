#!/usr/bin/env python3
"""
Compacts what fiware-manager staged into one object per device and run.

Its own entry point and not part of run_ingest.py because it works BY ARRIVAL: it takes
whatever is in the staging prefix, whatever hour it belongs to. It has no tenant either -
the raw feed carries none - so it must run once, not once per target.
"""

import logging

from crowd_predictions.etl.ote.etl import tidy_staging

logging.basicConfig(level=logging.INFO, format="%(message)s")


def main() -> int:
    written = tidy_staging()
    print(f"OTE archive: {len(written)} object(s) compacted")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        # Red, because the window run_ingest is about to read would be incomplete.
        print(f"ERROR - the compaction failed: {e}")
        raise SystemExit(1)
