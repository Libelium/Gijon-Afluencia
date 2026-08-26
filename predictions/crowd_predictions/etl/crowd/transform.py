"""
Transforms the raw signal (Smart Spot + LIDAR, already extracted by
CrowdExtract) into the crowd count per zone (3 cases - see lidar_estimation.py)
and exports it to one CSV per zone, same column format as
the reference prediction ETL (urn, type, [name], timestamp, <properties>) so that
helpers/uploader.py + platform.data.importation_job consume it the same way.

Entity type: CrowdFlowZone (crowd count aggregated per zone), not CrowdFlowObserved
(that one is per individual Smart Spot device).

ENABLE_SMARTSPOT/ENABLE_LIDAR (read in extract.py) already come applied here
with nothing extra: if LIDAR comes in empty (disabled or unavailable), every
zone falls to its "smartspot_only"/"lidar_only" case as appropriate, naturally,
via classify_zone_case() + zone_estimate(), with no need for additional logic in
this module.
"""

from datetime import datetime, timezone
from pathlib import Path

import json

import pandas as pd

from crowd_predictions.config import settings
from crowd_predictions.helpers.uploader import TIMESTAMP_COLUMN, TYPE_COLUMN, URN_COLUMN
from crowd_predictions.lidar_estimation import estimate_zone_totals
from crowd_predictions.zones_config import ZONES

# The entity type comes from CROWD_FLOW_ZONE_ENTITY_TYPE, read per call: per deployment.


# Smart Spot entities are keyed by `{serial}{suffix}` (the aggregated-counts
# datamodel of the platform this was built against). zones.json declares the full
# entity id, because that is what the reader matches against; what gets PUBLISHED is
# the bare serial. Empty disables the stripping.
SMARTSPOT_ENTITY_SUFFIX = "_CFO"


def _serial(device_id: str) -> str:
    """Entity id -> the device's serial, dropping the datamodel suffix."""
    if SMARTSPOT_ENTITY_SUFFIX and device_id.endswith(SMARTSPOT_ENTITY_SUFFIX):
        return device_id[: -len(SMARTSPOT_ENTITY_SUFFIX)]
    return device_id


class CrowdTransform:
    def __init__(self, smartspot_counts: dict, lidar_zone_counts: dict,
                 output_dir: str = settings.DEFAULT_PREDICTIONS_OUTPUT_DIR):
        self.smartspot_counts = smartspot_counts
        self.lidar_zone_counts = lidar_zone_counts
        self.output_dir = output_dir
        self.zone_totals = {}
        self.exported_files = []

    def transform(self) -> bool:
        self.zone_totals = estimate_zone_totals(self.lidar_zone_counts, self.smartspot_counts)
        self.exported_files = self._export_csvs()
        return True

    def _export_csvs(self) -> list:
        output_path = Path(self.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        now_dt = datetime.now(timezone.utc).replace(tzinfo=None)
        timestamp = now_dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        exported = []

        entity_type = settings.fusion().CROWD_FLOW_ZONE_ENTITY_TYPE

        for zone_id, totals in self.zone_totals.items():
            zone = ZONES[zone_id]
            entity_id = f"urn:ngsi-ld:{entity_type}:{zone_id}"

            row_data = {
                URN_COLUMN: entity_id,
                TYPE_COLUMN: entity_type,
                "name": zone.name,
                TIMESTAMP_COLUMN: timestamp,
                "occupancy": totals["occupancy"],
                "confidence": totals["confidence"],
                "case": totals["case"],
                # Published separately and never mixed into `occupancy` (see
                # lidar_estimation.zone_estimate). None -> NaN in the CSV: a
                # lidar_only/smartspot_only zone, or a mixed one with no LIDAR
                # reading this window.
                "smartspotSignal": totals["smartspot_signal"],
                "smartspotDeltaPct": totals["smartspot_delta_pct"],
            }
            # Flat lat/lon, not a nested GeoProperty - the bulk import CSV
            # (platform.data.importation_job) has no confirmed composite-column
            # encoding for GeoProperty.
            if zone.location is not None:
                row_data["latitude"], row_data["longitude"] = zone.location

            row_data["lidarSerial"] = json.dumps(zone.lidar_ids)
            row_data["smartspotSerial"] = json.dumps(
                [_serial(device_id) for device_id in zone.smartspot_ids])

            row = pd.DataFrame([row_data])

            filepath = output_path / f"{entity_id}.csv"
            row.to_csv(filepath, index=False)
            exported.append(str(filepath))

        return exported
