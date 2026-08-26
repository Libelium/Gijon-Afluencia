"""
Publishes the LIDAR aggregates as etl/crowd/load.py does: one CSV per entity ->
storage -> platform.data.importation_job. The CSVs are written here and not in transform.py
so that transform stays pure and the whole chain can be replayed over synthetic events.
Both entity types are PROVISIONAL: no LIDAR datamodel is registered in the platform yet.
"""

import json
import logging
import re
from pathlib import Path

import pandas as pd

from crowd_predictions.config import settings
from crowd_predictions.helpers.uploader import TIMESTAMP_COLUMN, TYPE_COLUMN, URN_COLUMN, upload_csv_files
from crowd_predictions.zones_config import ZONES

logger = logging.getLogger(__name__)

_URN_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _urn_fragment(value: str) -> str:
    """The device id comes from a URL path and can carry anything; the URN cannot."""
    return _URN_UNSAFE.sub("_", str(value)).strip("_") or "unknown"


def _timestamp(window_start) -> str:
    """The window START, not the clock: that is what makes a re-run of the same window
    republish the same sample instead of a second one dated differently."""
    return window_start.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class OteLoad:
    def __init__(self, zone_metrics: dict, device_metrics: dict, window_start,
                 output_dir: str = None, observed_metrics: dict = None):
        self.zone_metrics = zone_metrics
        # Per-sensor crowd metrics, apart from the device's health: the two answer
        # different questions and only one of them is withheld when a window is suspect.
        self.observed_metrics = observed_metrics or {}
        self.device_metrics = device_metrics
        self.window_start = window_start
        self.output_dir = output_dir or settings.ote().OTE_OUTPUT_DIR
        self.exported_files = []

    def load(self) -> bool:
        self.exported_files = self.export_csvs()
        if not self.exported_files:
            # Not "the window is empty" - an empty window still emits its zones as zeros.
            # This is no zone and no sensor at all: nothing is configured for this target.
            logger.error("Nothing to publish: no zone with a LIDAR of this target and no "
                         "sensor in the archive. Check zones_config and FIWARE_TARGETS.")
            return False
        results = upload_csv_files(self.exported_files)
        return len(results["successful"]) > 0 and len(results["failed"]) == 0

    def export_csvs(self) -> list:
        ote = settings.ote()
        output_path = Path(self.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        timestamp = _timestamp(self.window_start)

        exported = []
        for zone_id, attributes in sorted(self.zone_metrics.items()):
            row = {
                URN_COLUMN: f"urn:ngsi-ld:{ote.OTE_ZONE_ENTITY_TYPE}:{_urn_fragment(zone_id)}",
                TYPE_COLUMN: ote.OTE_ZONE_ENTITY_TYPE,
                TIMESTAMP_COLUMN: timestamp,
            }
            zone = ZONES.get(zone_id)
            if zone is not None:
                row["name"] = zone.name
            for key, value in attributes.items():
                # Transits go as a JSON string in one cell: one attribute per pair would
                # be hundreds of attributes with a few dozen sensors.
                row[key] = json.dumps(value, sort_keys=True) if isinstance(value, dict) else value
            exported.append(self._write(output_path, row))

        for device_id, attributes in sorted(self.observed_metrics.items()):
            row = {
                URN_COLUMN: f"urn:ngsi-ld:{ote.OTE_OBSERVED_ENTITY_TYPE}:{_urn_fragment(device_id)}",
                TYPE_COLUMN: ote.OTE_OBSERVED_ENTITY_TYPE,
                TIMESTAMP_COLUMN: timestamp,
                "serial": device_id,
                **attributes,
            }
            exported.append(self._write(output_path, row))

        for device_id, attributes in sorted(self.device_metrics.items()):
            row = {
                URN_COLUMN: f"urn:ngsi-ld:{ote.OTE_DEVICE_ENTITY_TYPE}:{_urn_fragment(device_id)}",
                TYPE_COLUMN: ote.OTE_DEVICE_ENTITY_TYPE,
                TIMESTAMP_COLUMN: timestamp,
                # "serial" and not "device_id": it is the sensor's serial, which is what
                # the URL the LIDAR posts to carries and the only id the raw feed has.
                "serial": device_id,
                **attributes,
            }
            exported.append(self._write(output_path, row))

        return exported

    @staticmethod
    def _write(output_path: Path, row: dict) -> str:
        # The file name without extension IS the URN: upload_csv_files' contract.
        filepath = output_path / f"{row[URN_COLUMN]}.csv"
        pd.DataFrame([row]).to_csv(filepath, index=False)
        return str(filepath)
