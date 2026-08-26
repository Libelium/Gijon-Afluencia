"""Compacts the small dumps of fiware-manager into one object per device, run and
CLOCK HOUR, and empties the staging prefix. BY ARRIVAL, not by interval: a dump can land
after its hour has passed, and splitting by interval would orphan it forever. Cheap
because gzip accepts concatenated members, so joining is a byte-level operation.

Capped at the hour because that is the unit the ingestion reads: an object covering more
gets downloaded and re-read whole by every run overlapping it (see _by_hour).
"""

import gzip
import json
import logging
import os
import re
import shutil
import tempfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from crowd_predictions.config import settings

logger = logging.getLogger(__name__)

# Fallback when the caller does not say; the real default is OTE_DOWNLOAD_WORKERS. The
# constant, not a copy of its value, so the module stays usable and testable without
# reading the environment and the two cannot drift.
DOWNLOAD_WORKERS = settings.DEFAULT_OTE_DOWNLOAD_WORKERS

# The receiver's dumps: `<epoch ms>-<pid>-<seq>`. The 10-digit floor is what stops it
# from also matching an archived name, whose first field is a date of 8.
_DUMP_NAME = re.compile(r"^(\d{10,})-(\d+)-(\d+)\.ndjson\.gz$")
# What this module writes, and the only thing the reader accepts as data. To the
# MILLISECOND: the receiver runs two workers, so two dumps of one device can share a
# second, and at second resolution two runs could produce the same key - the second
# overwriting the first, whose dumps were already deleted.
_ARCHIVED_NAME = re.compile(r"^(\d{8})-(\d{9})-(\d{9})\.ndjson\.gz$")

MANIFEST_SUFFIX = ".manifest.json"


class CompactionIncomplete(RuntimeError):
    """Some devices kept their dumps staged, so the window is NOT complete.

    Raised after trying every device: publishing a window missing sensors would look
    green and, with Timescale's ON CONFLICT DO NOTHING, could not be corrected.
    """

    def __init__(self, written: list, failed: list):
        super().__init__(f"{len(failed)} device(s) could not be compacted: {sorted(failed)}")
        self.written = written
        self.failed = failed


def dump_timestamp(key: str):
    """The instant in the dump's name, which is the START of its flush window."""
    match = _DUMP_NAME.match(os.path.basename(key))
    if match is None:
        return None
    return datetime.fromtimestamp(int(match.group(1)) / 1000, tz=timezone.utc)


def archive_interval(key: str):
    """`YYYYMMDD-HHMMSSfff-HHMMSSfff.ndjson.gz` -> (first dump start, last dump start).

    None if the name is not one of ours, which is also what keeps the manifests and the
    receiver's own dumps out of the reader. Lives here, next to archived_key(), because
    a reader parsing the name on its own is how it silently stopped matching.
    """
    match = _ARCHIVED_NAME.match(os.path.basename(key))
    if match is None:
        return None
    day, first, last = match.groups()
    moments = tuple(datetime.strptime(day + field, "%Y%m%d%H%M%S%f").replace(tzinfo=timezone.utc)
                    for field in (first, last))
    if moments[1] < moments[0]:
        # Cannot happen: an object never spans more than a clock hour, let alone midnight.
        # A name written before that rule would be read backwards, so it is refused.
        logger.error(f"Archived name with an interval that goes backwards, ignored: {key}")
        return None
    return moments


def pending_by_device(storage, incoming_prefix: str) -> dict:
    """Everything staged, grouped by device id (the first path segment) and chronological."""
    prefix = incoming_prefix.strip("/") + "/"
    by_device = defaultdict(list)
    for key in storage.list_prefix(prefix):
        at = dump_timestamp(key)
        if at is None:
            logger.warning(f"Ignoring key with an unexpected name in the staging area: {key}")
            continue
        rest = key[len(prefix):]
        if "/" not in rest:
            logger.warning(f"Ignoring staged key with no device id: {key}")
            continue
        by_device[rest.split("/", 1)[0]].append((at, key))
    return {device_id: [key for _at, key in sorted(dumps)]
            for device_id, dumps in by_device.items()}


def archived_key(raw_prefix: str, device_id: str, keys: list) -> str:
    """`<raw>/<device_id>/YYYY/MM/DD/YYYYMMDD-HHMMSSfff-HHMMSSfff.ndjson.gz`. From the dump
    NAMES, which are window starts, so content can spill past the upper bound.

    To the MILLISECOND, which is the resolution the dump names carry: with less, two runs
    of one device could produce the same key and the second would overwrite the first,
    whose dumps had already been deleted. At this resolution two runs can only collide by
    sharing their first and last dump, and a dump is deleted as soon as it is archived, so
    colliding would mean holding the same content.
    """
    first, last = dump_timestamp(keys[0]), dump_timestamp(keys[-1])
    name = f"{first:%Y%m%d-%H%M%S}{first.microsecond // 1000:03d}-" \
           f"{last:%H%M%S}{last.microsecond // 1000:03d}.ndjson.gz"
    return f"{raw_prefix.strip('/')}/{device_id}/{first:%Y/%m/%d}/{name}"


def manifest_key(manifest_prefix: str, archived: str) -> str:
    """The manifest of an archived object, in its OWN prefix.

    Not next to the object: recover() has to list every manifest on every run, and beside
    the data that means walking the whole history - a few dozen sensors of hourly objects are
    ~315k keys a year - to find the handful that matter.
    """
    device_id, name = archived.strip("/").split("/")[-5], os.path.basename(archived)
    return f"{manifest_prefix.strip('/')}/{device_id}/{name}{MANIFEST_SUFFIX}"


def _write_manifest(storage, key: str, sources: list, size_bytes: int,
                    manifest_prefix: str) -> str:
    """Written before deleting the sources and removed last: while it exists it means
    an unfinished run, which is the only state `recover()` needs."""
    manifest_key_ = manifest_key(manifest_prefix, key)
    body = json.dumps({"archived": key, "bytes": size_bytes, "sources": sources},
                      indent=1).encode()
    _upload_bytes(storage, manifest_key_, body)
    return manifest_key_


def _upload_bytes(storage, key: str, body: bytes) -> None:
    """The storage contract only uploads from a path, so bytes go via a temp file."""
    with tempfile.NamedTemporaryFile(delete=False) as handle:
        handle.write(body)
        path = handle.name
    try:
        storage.upload_file(key, path)
    finally:
        os.unlink(path)


def _download_bytes(storage, key: str) -> bytes:
    with tempfile.NamedTemporaryFile(delete=False) as handle:
        path = handle.name
    try:
        storage.download_file(key, path)
        with open(path, "rb") as handle:
            return handle.read()
    finally:
        os.unlink(path)


def compact_archive(storage, incoming_prefix: str, raw_prefix: str,
                    manifest_prefix: str, workers: int = DOWNLOAD_WORKERS) -> list:
    """Joins everything staged per device and empties the prefix. Deletes by EXPLICIT
    list, never by prefix: a dump landing mid-run must survive to the next run.

    Tries every device and then raises CompactionIncomplete if any failed: one broken
    sensor must not stop the others, but it must not pass for a complete window either.
    """
    written, failed = [], []
    for device_id, keys in sorted(pending_by_device(storage, incoming_prefix).items()):
        for hour_keys in _by_hour(keys):
            try:
                key = _compact_device(storage, device_id, hour_keys, raw_prefix,
                                      manifest_prefix, workers)
            except Exception as e:
                logger.error(f"Could not compact {len(hour_keys)} dumps of {device_id}: {e}")
                key = None
            if key:
                written.append(key)
            elif device_id not in failed:
                failed.append(device_id)

    if failed:
        logger.error(f"{len(written)} object(s) compacted, {len(failed)} device(s) left staged")
        raise CompactionIncomplete(written, failed)
    return written


def _by_hour(keys: list) -> list:
    """One group per UTC CLOCK HOUR of the dump name, chronological.

    The hour and not the day because the hour is what the ingestion reads: an object
    spanning more than one is downloaded and re-read WHOLE by every run that overlaps it,
    so after a day of backlog each of the 24 catch-up runs re-reads the entire day.
    Capping at the hour also keeps the name honest - it states its interval with one
    date, so it could never have described an object spanning more than 24 h anyway.

    In steady state this changes nothing: one run per hour already produced one object.
    """
    by_hour = defaultdict(list)
    for key in keys:
        by_hour[dump_timestamp(key).replace(minute=0, second=0, microsecond=0)].append(key)
    return [by_hour[hour] for hour in sorted(by_hour)]


def _compact_device(storage, device_id: str, keys: list, raw_prefix: str,
                    manifest_prefix: str, workers: int = DOWNLOAD_WORKERS):
    key = archived_key(raw_prefix, device_id, keys)
    path, size_bytes = _join_dumps(storage, keys, workers)
    try:
        # MANIFEST FIRST, object second. The other way round, a process KILLED between the
        # upload and the manifest (SIGKILL, OOM, eviction - the very death recover() exists
        # for, and one no except clause sees) left an object with a valid data name, no
        # manifest and its dumps still staged: the next run archived them again and the
        # same frames stayed in the archive twice, for ever.
        # This order has no such hole: whatever the moment of death, recover() finds the
        # manifest and re-verifies the object, which either exists whole (dumps deleted) or
        # does not (manifest dropped, dumps kept).
        manifest = _write_manifest(storage, key, keys, size_bytes, manifest_prefix)
        storage.upload_file(key, path)

        if not _is_intact(storage, key, size_bytes):
            # The archived object is garbage: it is removed here so it cannot be read as
            # data, and the dumps stay staged for the next run to try again.
            logger.error(f"The archived {key} does not match what was uploaded - "
                         "discarded, sources kept")
            _discard(storage, key, manifest)
            return None
    finally:
        os.unlink(path)

    # In ONE call where the backend supports it: one DELETE per dump was half the run.
    storage.delete_files(keys)
    storage.delete_file(manifest)

    logger.info(f"Compacted {device_id}: {len(keys)} dumps -> {key} "
                f"({size_bytes / 1024:.0f} KB)")
    return key


def _join_dumps(storage, keys: list, workers: int = DOWNLOAD_WORKERS) -> tuple:
    """The dumps concatenated into a temp file -> (path, bytes).

    A PATH and not bytes: holding every dump plus the join in memory is two copies of the
    hour. Downloaded in PARALLEL because the cost is latency, not bytes - 60 dumps a
    sensor, one round trip each, was most of a run - and written back IN ORDER, which the
    gap logic of presence_segments() depends on.
    """
    handle, path = tempfile.mkstemp(suffix=".ndjson.gz")
    os.close(handle)
    parts = []
    try:
        with ThreadPoolExecutor(max_workers=max(1, min(workers, len(keys)))) as pool:
            parts = list(pool.map(lambda key: _download_to_temp(storage, key), keys))
        with open(path, "wb") as joined:
            for part in parts:
                with open(part, "rb") as source:
                    shutil.copyfileobj(source, joined)
        return path, os.path.getsize(path)
    except Exception:
        os.unlink(path)
        raise
    finally:
        for part in parts:
            if part and os.path.exists(part):
                os.unlink(part)


def _download_to_temp(storage, key: str) -> str:
    handle, path = tempfile.mkstemp(suffix=".part.gz")
    os.close(handle)
    try:
        storage.download_file(key, path)
        return path
    except Exception:
        os.unlink(path)
        raise


def _discard(storage, *keys: str) -> None:
    """Best effort: a leftover here is noise, and raising would hide the real error."""
    for key in keys:
        try:
            storage.delete_file(key)
        except Exception as e:
            logger.error(f"Could not remove {key}: {e}")


def _is_intact(storage, key: str, expected_bytes: int) -> bool:
    """Re-reads it: the size catches a truncated upload, reading the gzip a corrupt one.

    In STREAMING and never gzip.decompress(): decompressing materialises the whole text,
    ~21 MB per sensor-hour, so a device that fell behind for days asked for over a GB in a
    single object - dying exactly when the compaction matters most, and every run after.
    """
    handle, path = tempfile.mkstemp(suffix=".verify.gz")
    os.close(handle)
    try:
        storage.download_file(key, path)
        actual = os.path.getsize(path)
        if actual != expected_bytes:
            logger.error(f"{key}: {actual} bytes uploaded, {expected_bytes} expected")
            return False
        with gzip.open(path, "rb") as body:
            while body.read(1 << 20):
                pass
        return True
    except Exception as e:
        logger.error(f"{key} cannot be verified: {e}")
        return False
    finally:
        if os.path.exists(path):
            os.unlink(path)


def recover(storage, manifest_prefix: str) -> int:
    """Finishes a run that died between archiving and deleting: a surviving
    manifest means the sources were never removed, and would be compacted twice.

    RE-VERIFIES the archived object first. The manifest only proves the run died, not
    that the upload was good, and deleting the dumps of a corrupt object is the one
    irreversible mistake in the whole chain.
    """
    finished = 0
    for key in storage.list_prefix(manifest_prefix.strip("/") + "/"):
        if not key.endswith(MANIFEST_SUFFIX):
            continue
        try:
            manifest = json.loads(_download_bytes(storage, key).decode())
            archived, sources = manifest["archived"], manifest.get("sources", [])
            if not _is_intact(storage, archived, manifest["bytes"]):
                # The dumps are the only surviving copy: the archived object goes, they stay.
                logger.error(f"{archived} is unusable: discarded, its {len(sources)} "
                             "dumps are kept for the next run")
                _discard(storage, archived, key)
                continue
            logger.warning(f"Unfinished run found ({key}): removing "
                           f"{len(sources)} dumps already archived")
            for source in sources:
                try:
                    storage.delete_file(source)
                except Exception as e:
                    logger.error(f"Could not delete {source}: {e}")
            storage.delete_file(key)
            finished += 1
        except Exception as e:
            logger.error(f"Could not process the manifest {key}: {e}")
    return finished
