"""
Extraction of the input data (Smart Spot + LIDAR) for the crowd ETL.

Segregated by environment variables (ENABLE_SMARTSPOT / ENABLE_LIDAR) so that in
the future an on-premise deployment with only Smart Spot (with no LIDAR
installed) can run just the same, without touching code - simply with
ENABLE_LIDAR=false.

DATA_SOURCE controls where BOTH signals come from, and they always come from the
same side - a run half synthetic and half real would fuse two unrelated worlds:
  - "synthetic": fixtures.generate_events() collapsed into a count per
    device, plus a synthetic LIDAR count per zone. No real sensors involved.
  - "real" (default): both read the platform. Smart Spot from `CrowdFlowObserved`
    (helpers/smartspot_history), LIDAR from `CrowdFlowLidarZone`
    (helpers/lidar_zone_history), each as the CURRENT reading per device/zone.
    A device or zone with no reading this window is simply absent, and
    lidar_estimation.py already treats that as "no signal from this side".

Both are handed to the fusion as {id: count}, never as raw detections: what the
platform publishes is an aggregate, and the identity-carrying `CrowdFlowEvent` is
neither published by us nor something to pull into a live ETL (see
helpers/smartspot_history.py for the double-counting caveat that follows).

Note: the flags/config are read in __init__, not at module level, so that
CrowdExtract can be instantiated several times with different config within the
same process (tests) without depending on reloading the module.
"""

import logging

from crowd_predictions.config import settings
from crowd_predictions.fixtures import generate_events, generate_lidar_zone_counts
from crowd_predictions.helpers.smartspot_history import counts_from_events

logger = logging.getLogger(__name__)


class CrowdExtract:
    def __init__(self):
        sensors = settings.sensors()
        fusion = settings.fusion()
        self.enable_smartspot = sensors.ENABLE_SMARTSPOT
        self.enable_lidar = sensors.ENABLE_LIDAR
        self.data_source = fusion.DATA_SOURCE
        self.synthetic_days = fusion.SYNTHETIC_DAYS

        self.smartspot_counts = {}
        self.lidar_zone_counts = {}

    def extract(self) -> bool:
        if self.data_source not in ("synthetic", "real"):
            raise ValueError(f"Unknown DATA_SOURCE: {self.data_source}. Use 'synthetic' or 'real'")

        # Loud on every run: synthetic occupancy published against a real tenant is
        # indistinguishable from measured data once it is in the platform.
        if self.data_source == "synthetic":
            logger.warning("DATA_SOURCE=synthetic: publishing MADE-UP occupancy and training on "
                           "it. No sensor is being read. Set DATA_SOURCE=real in production.")

        # Generated ONCE and shared by the two synthetic sources: the fixture LIDAR
        # count per zone is derived from these very events, so the two signals
        # describe the same made-up afternoon instead of two unrelated ones.
        events = (generate_events(days=self.synthetic_days)
                  if self.data_source == "synthetic" else [])

        self.smartspot_counts = self._load_smartspot_counts(events) if self.enable_smartspot else {}
        self.lidar_zone_counts = self._load_lidar_zone_counts(events) if self.enable_lidar else {}
        return True  # only fails on exception

    def _load_smartspot_counts(self, events: list) -> dict:
        """{device_id: people counted} for this window."""
        if self.data_source == "synthetic":
            return counts_from_events(events)
        from crowd_predictions.helpers.smartspot_history import load_smartspot_counts
        return load_smartspot_counts()

    def _load_lidar_zone_counts(self, events: list) -> dict:
        if self.data_source == "synthetic":
            return generate_lidar_zone_counts(events)
        from crowd_predictions.helpers.lidar_zone_history import load_lidar_zone_counts
        return load_lidar_zone_counts()
