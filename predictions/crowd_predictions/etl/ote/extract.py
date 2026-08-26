"""Reads a window of the compacted archive, yielding events one at a time.

The file name is the START of its dump window, hence OTE_READ_MARGIN_SECONDS: without
it the first minutes of every run go missing and nothing fails.
"""

import gzip
import json
import logging
import os
import tempfile
from datetime import datetime, timedelta, timezone

from crowd_predictions.config import settings
from crowd_predictions.config.config import get_storage
from crowd_predictions.etl.ote.compact_archive import archive_interval
from crowd_predictions.etl.ote.transform import census_frame, new_census

logger = logging.getLogger(__name__)

def _to_utc(ts_ms) -> datetime:
    return datetime.fromtimestamp(int(ts_ms) / 1000.0, tz=timezone.utc)


class OteExtract:
    """Raw window -> (device_id, event) stream, plus the frame census of §4, which counts
    empty frames and so cannot be derived from the events."""

    def __init__(self, window_start: datetime, window_end: datetime, device_ids: list = None,
                 storage=None, margin_seconds: int = None, raw_prefix: str = None):
        ote = settings.ote()
        self.window_start = window_start
        self.window_end = window_end
        self.raw_prefix = (raw_prefix if raw_prefix is not None else ote.OTE_RAW_PREFIX).rstrip("/")
        self.margin_seconds = (ote.OTE_READ_MARGIN_SECONDS if margin_seconds is None
                               else margin_seconds)
        self.spill = timedelta(seconds=self.margin_seconds)
        self.lookback_days = ote.OTE_ARCHIVE_LOOKBACK_DAYS
        # Files that could not be read at all: the window is incomplete, not merely quiet.
        self.unreadable = []
        # Injected for the tests, resolved lazily: get_storage() reads the environment.
        self._storage = storage
        self._device_ids = device_ids if device_ids else (ote.device_id_list() or None)

        # device_id -> folded frame census, filled while streaming. FOLDED, not a list of
        # frames: a few dozen sensors at 10 fps for an hour is 1.3 M rows and ~145 MB of tuples.
        self.frames_by_device = {}

    @property
    def storage(self):
        if self._storage is None:
            self._storage = get_storage()
        return self._storage

    def device_ids(self) -> list:
        """Configured device ids, or discovered by listing the raw prefix."""
        if self._device_ids is None:
            prefix = f"{self.raw_prefix}/"
            self._device_ids = sorted(
                found[len(prefix):].strip("/")
                for found in self.storage.list_subprefixes(prefix)
            )
            logger.info(f"OTE device ids discovered under '{prefix}': {self._device_ids}")
        return self._device_ids

    def keys_for_device(self, device_id: str) -> list:
        """The archived files that MAY carry events of the window, in chronological order.

        By INTERVAL OVERLAP, not by start: an archived object covers whatever was staged
        in its run, which is unbounded, so a run after an outage produces a single object
        starting hours before the window it still contains.
        """
        read_from = self.window_start - timedelta(seconds=self.margin_seconds)
        keys = []
        for day in self._days(read_from, self.window_end):
            prefix = f"{self.raw_prefix}/{device_id}/{day.strftime('%Y/%m/%d')}/"
            for key in self.storage.list_prefix(prefix):
                interval = archive_interval(key)
                if interval is None:
                    continue
                start, last_dump = interval
                # The upper bound is a dump START, so its content spills one flush past it.
                if start < self.window_end and last_dump + self.spill >= read_from:
                    keys.append((start, key))
        return [key for _, key in sorted(keys)]

    def _days(self, start: datetime, end: datetime) -> list:
        """The day directories to list. Widened backwards by OTE_ARCHIVE_LOOKBACK_DAYS:
        an object is filed under the day it STARTED, which can precede the window."""
        day = (start - timedelta(days=self.lookback_days)).replace(
            hour=0, minute=0, second=0, microsecond=0)
        days = []
        while day <= end:
            days.append(day)
            day += timedelta(days=1)
        return days

    def iter_events(self):
        """Yields (device_id, event) for the stage-4 events inside the window, chronological
        within each device, so presence_segments() can close segments with no global sort."""
        for device_id in self.device_ids():
            census = self.frames_by_device.setdefault(device_id, new_census())
            for key in self.keys_for_device(device_id):
                for line in self._read_lines(key):
                    yield from self._frame_events(device_id, line, census)

    def _frame_events(self, device_id: str, line: dict, census: dict):
        """One NDJSON line = one frame: censuses it and yields its events."""
        # Nothing is filtered by stage or by event type. The push API only ever publishes
        # the aggregator: measured over the whole of a sample push, `sourceId` is
        # "TrackingAggregator" in every single one and the only event types are
        # OTETrajectoryUpdate and OTEIdLost. The lower stages and OTESingleDetection exist
        # only in the old streaming API, which this deployment does not use.
        events = [event for event in (line.get("events") or [])
                  if isinstance(event, dict) and self._keep(event)]

        frame_ts = line.get("timeStamp")
        if frame_ts is None and events:
            frame_ts = events[0].get("timeStamp")
        if frame_ts is None:
            return
        frame_at = _to_utc(frame_ts)
        if not (self.window_start <= frame_at < self.window_end):
            return

        in_window = [event for event in events
                     if self.window_start <= _to_utc(event["timeStamp"]) < self.window_end]
        # "Empty" = no tracked object: the sensor is alive and saw nobody.
        census_frame(census, frame_at, len(in_window))
        for event in in_window:
            yield device_id, event

    @staticmethod
    def _keep(event: dict) -> bool:
        """An event without an id or without an instant cannot be placed in a segment."""
        return event.get("objectId") and event.get("timeStamp") is not None

    def _read_lines(self, key: str):
        """Parsed lines of one raw file. Via a temp file: StorageType only downloads to
        a path, and at most one is on disk at a time."""
        handle, path = tempfile.mkstemp(suffix=".ndjson.gz")
        os.close(handle)
        try:
            self.storage.download_file(key, path)
            with gzip.open(path, "rt", encoding="utf-8") as raw:
                for number, text in enumerate(raw, start=1):
                    text = text.strip()
                    if not text:
                        continue
                    try:
                        line = json.loads(text)
                    except ValueError:
                        # One corrupt line must not lose the whole window: a truncated
                        # tail is the expected damage in an append-only dump.
                        logger.warning(f"Unparseable line {number} in '{key}', skipped")
                        continue
                    if isinstance(line, dict):
                        yield line
        except Exception as error:
            # A gzip member broken in the MIDDLE (a partial upload) aborts the whole
            # file, losing every member after it - unlike a truncated last line, which
            # is expected damage. Recorded so the run fails instead of publishing a hole.
            self.unreadable.append(key)
            logger.error(f"Could not read '{key}', the rest of the file is LOST: {error}")
        finally:
            if os.path.exists(path):
                os.remove(path)
