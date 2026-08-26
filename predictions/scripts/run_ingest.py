#!/usr/bin/env python3
"""
Ingests one window of the LIDAR archive: reads, aggregates and publishes, per target.

Does NOT compact the staging area - scripts/compact_ote_archive.py does, and
scripts/run_ote.py chains the two. With no arguments it takes the previous complete
window; --from/--to reprocess an explicit one, which republishes the same sample because
it is dated with the window start.
"""

import argparse
import logging

from crowd_predictions.etl.ote.etl import ingest_window, resolve_window

logging.basicConfig(level=logging.INFO, format="%(message)s")


def main() -> int:
    parser = argparse.ArgumentParser(description="LIDAR (OTE) window ingestion")
    parser.add_argument("--from", dest="window_from", help="ISO-8601 UTC start, inclusive")
    parser.add_argument("--to", dest="window_to", help="ISO-8601 UTC end, exclusive")
    args = parser.parse_args()

    try:
        window_start, window_end = resolve_window(args.window_from, args.window_to)
    except ValueError as e:
        parser.error(str(e))

    print(f"OTE ingestion window {window_start.isoformat()} -> {window_end.isoformat()}")
    return ingest_window(window_start, window_end)


if __name__ == "__main__":
    exit_code = main()
    print("OK - LIDAR window ingested and published for every target" if exit_code == 0
          else "ERROR - the ingestion failed for at least one target, see the logs above")
    raise SystemExit(exit_code)
