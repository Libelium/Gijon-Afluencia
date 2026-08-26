"""
The LIDAR raw ingestion on the BaseETL contract: compact the staged dumps, then
aggregate one window of `ote/raw/` per zone and per sensor. Separate steps because the
first goes by ARRIVAL and the second by CLOCK HOUR. Idempotent: samples are dated with
the window start.
"""

import logging
import os
from datetime import datetime, timedelta, timezone

import pandas as pd

from crowd_predictions.config import settings
from crowd_predictions.config.config import get_storage
from crowd_predictions.etl.base_etl import BaseETL
from crowd_predictions.etl.ote.compact_archive import CompactionIncomplete, compact_archive, recover
from crowd_predictions.etl.ote.extract import OteExtract
from crowd_predictions.etl.ote.load import OteLoad
from crowd_predictions.etl.ote.transform import (
    device_metrics,
    observed_metrics,
    presence_segments,
    tracks,
    zone_metrics,
)
from crowd_predictions.helpers.fiware_targets import run_for_each_target, target_slug
from crowd_predictions.zones_config import ZONES, device_to_zone_map

logger = logging.getLogger(__name__)


def zones_with_lidar(device_ids: list = None) -> list:
    """Zones with a sensor installed: they are emitted as a real zero when they report
    nothing, unlike the zones with no LIDAR, where a zero would be a lie.

    Restricted to the target's OWN sensors when FIWARE_TARGETS declares them: ZONES is
    global, so without this every tenant would publish every other tenant's zones.
    """
    own = set(device_ids or [])
    return sorted(zone_id for zone_id, zone in ZONES.items()
                  if zone.lidar_ids and (not own or own & set(zone.lidar_ids)))


class OteETL(BaseETL):
    def __init__(self, window_start, window_end, output_dir: str = None, storage=None):
        ote = settings.ote()
        self.window = (window_start, window_end)
        self.gap_seconds = ote.OTE_TRACK_GAP_SECONDS
        self.stationary_max_m = ote.OTE_STATIONARY_MAX_DISPLACEMENT_M
        self.published_labels = ote.label_attrs()
        self.device_ids = ote.device_id_list()
        # One subdirectory per target: sharing it would mix the targets' CSVs.
        self.output_dir = os.path.join(output_dir or ote.OTE_OUTPUT_DIR, target_slug())
        self.storage = storage
        self.extractor = None
        self.loader = None

        self.segments = []
        self.tracks = []
        self.zone_metrics = {}
        self.observed_metrics = {}
        self.device_metrics = {}

    def init_etl(self) -> bool:
        return True

    def extract(self) -> bool:
        # Opens the archive, but reads nothing: iter_events() is a generator that
        # transform() consumes, so one hour of a few dozen sensors never lands in memory.
        self.extractor = OteExtract(*self.window, storage=self.storage)
        return True

    def transform(self) -> bool:
        self.segments = presence_segments(self.extractor.iter_events(), self.gap_seconds,
                                          window_end=self.window[1])
        self.tracks = tracks(self.segments, self.published_labels)
        # An unmapped device still gets its device entity and
        # only drops out of the zone aggregate, with a warning.
        zone_of_device = device_to_zone_map().get
        self.zone_metrics = zone_metrics(self.tracks, self.segments, self.window, zone_of_device,
                                         self.published_labels, self.stationary_max_m,
                                         zone_ids=zones_with_lidar(self.device_ids),
                                         label_priority=self.published_labels)
        # Per SENSOR as well as per zone: the sensors of a zone sit far enough apart or
        # more, so the aggregate hides which of its six carries the traffic.
        self.observed_metrics = observed_metrics(self.tracks, self.segments, self.window,
                                                 self.published_labels, self.stationary_max_m,
                                                 sorted(self.extractor.frames_by_device),
                                                 label_priority=self.published_labels)
        self.device_metrics = device_metrics(self.extractor.frames_by_device, self.window)
        logger.info(f"OTE window {self.window[0].isoformat()} -> {self.window[1].isoformat()}: "
                    f"{len(self.segments)} segments, {len(self.tracks)} tracks, "
                    f"{len(self.device_metrics)} sensors")
        return True

    def load(self) -> bool:
        """Publishes the sensors always and the zones only if the window can be believed.

        The asymmetry is the whole point. Zone metrics are what feeds the model and what
        Timescale ingests with ON CONFLICT DO NOTHING, so a wrong zero is PERMANENT:
        publishing it and then going red leaves the bad sample behind for good. The device
        entities are the opposite - they are the signal that says whether an hour was quiet
        or the read was broken, so they have to go out precisely when things went wrong.
        """
        trustworthy = self._window_is_trustworthy()
        self.loader = OteLoad({} if trustworthy is False else self.zone_metrics,
                              self.device_metrics, self.window[0], output_dir=self.output_dir,
                              observed_metrics={} if trustworthy is False
                              else self.observed_metrics)
        return self.loader.load() and trustworthy

    def _window_is_trustworthy(self) -> bool:
        unreadable = self.extractor.unreadable
        if unreadable:
            logger.error(f"{len(unreadable)} archived file(s) could not be read, so the "
                         f"window is INCOMPLETE and NO zone is published: {unreadable}")
            return False
        if not any(census["frames"] for census in self.extractor.frames_by_device.values()):
            logger.error("Not a single frame in the whole window. Check the archive prefix, "
                         "the credentials and the receiver: NO zone is published, because a "
                         "zero here cannot be told from a broken read.")
            return False
        if not self.zone_metrics:
            # Reaches here with sensors reporting: their ids are not in zones_config, so
            # everything read is dropped and only the device entities would go out.
            logger.error(f"No zone to publish for these devices ({self.device_ids or 'all'}): "
                         "check that the ids match the lidar_ids of zones_config.")
            return False
        return True


def previous_window(now: datetime = None, window_seconds: int = None) -> tuple:
    """The last COMPLETE window, aligned to the epoch so consecutive runs tile the
    timeline without gaps or overlap and a re-run lands on the same window."""
    window_seconds = window_seconds or settings.ote().OTE_WINDOW_SECONDS
    now = now or datetime.now(timezone.utc)
    aligned = int(now.timestamp()) // window_seconds * window_seconds
    end = datetime.fromtimestamp(aligned, tz=timezone.utc)
    return end - timedelta(seconds=window_seconds), end


def tidy_staging(storage=None) -> list:
    """Finishes any half-done run and compacts whatever the receiver has staged.

    ONCE PER RUN, outside the per-target loop: the staging prefix is not segregated by
    tenant, so the second target would find it already empty.
    """
    ote = settings.ote()
    storage = storage or get_storage()
    recovered = recover(storage, ote.OTE_MANIFEST_PREFIX)
    if recovered:
        logger.warning(f"{recovered} unfinished run(s) closed before archiving")
    return compact_archive(storage, ote.OTE_INCOMING_PREFIX, ote.OTE_RAW_PREFIX,
                           ote.OTE_MANIFEST_PREFIX, ote.OTE_DOWNLOAD_WORKERS)


def ingest_window(window_start: datetime, window_end: datetime) -> int:
    """The window for every tenant/scope, reading the archive as it already is.

    Compacting is NOT done here: it goes by arrival and this goes by clock hour, so they
    are separate entry points (scripts/run_ote.py chains them). Compacting first is what
    lets this read a COMPLETE hour, whose dumps may have arrived across several runs.
    """
    return run_for_each_target(
        lambda _tenant, _scope: OteETL(window_start, window_end).execute_once(), logger)


def resolve_window(from_text: str = None, to_text: str = None) -> tuple:
    """Explicit window, or the previous complete one. A naive datetime is read as UTC:
    the raw feed is UTC everywhere and guessing local time would shift the window."""
    if bool(from_text) != bool(to_text):
        raise ValueError("--from and --to go together")
    if not from_text:
        return previous_window()

    window = tuple(pd.Timestamp(text).to_pydatetime() for text in (from_text, to_text))
    window = tuple(moment.astimezone(timezone.utc) if moment.tzinfo
                   else moment.replace(tzinfo=timezone.utc) for moment in window)
    if window[0] >= window[1]:
        raise ValueError("--from must be earlier than --to")
    return window


def compact_and_ingest(window_start: datetime, window_end: datetime) -> int:
    """Compaction and then ingestion, aborting on the first failure.

    Aborting because a broken compaction leaves part of the window staged, so the
    ingestion would publish metrics missing data - and would look green. Stopping lets
    the next run pick everything up, which is what compacting by arrival is for.
    """
    try:
        written = tidy_staging()
    except CompactionIncomplete as incomplete:
        logger.error(f"COMPACTION INCOMPLETE, nothing is published: {incomplete}")
        return 1
    except Exception:
        logger.exception("COMPACTION FAILED, nothing is published")
        return 1
    logger.info(f"{len(written)} object(s) compacted")
    return ingest_window(window_start, window_end)
