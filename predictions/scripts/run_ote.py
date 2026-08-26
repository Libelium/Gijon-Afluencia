#!/usr/bin/env python3
"""
THE CronJob one: compacts the staging area and then ingests the window, in that order.

The two halves also exist on their own (compact_ote_archive.py, run_ingest.py) because
one goes by ARRIVAL and the other by CLOCK HOUR. This chains them and aborts if the
compaction fails - see etl.compact_and_ingest.
"""

import argparse
import logging

from crowd_predictions.etl.ote.etl import compact_and_ingest, resolve_window

logging.basicConfig(level=logging.INFO, format="%(message)s")


def main() -> int:
    parser = argparse.ArgumentParser(description="LIDAR (OTE): compaction + ingestion")
    parser.add_argument("--from", dest="window_from", help="ISO-8601 UTC start, inclusive")
    parser.add_argument("--to", dest="window_to", help="ISO-8601 UTC end, exclusive")
    args = parser.parse_args()

    try:
        window_start, window_end = resolve_window(args.window_from, args.window_to)
    except ValueError as e:
        parser.error(str(e))

    print(f"OTE window {window_start.isoformat()} -> {window_end.isoformat()}")
    return compact_and_ingest(window_start, window_end)


if __name__ == "__main__":
    exit_code = main()
    print("OK - archive compacted and window published" if exit_code == 0
          else "ERROR - see the logs above")
    raise SystemExit(exit_code)
