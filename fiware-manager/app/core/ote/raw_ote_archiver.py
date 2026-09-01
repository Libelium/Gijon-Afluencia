"""Buffers the OTE frames verbatim and writes them to a STAGING prefix, one gzipped
NDJSON object per device and window; the ingest cron consolidates them under
`ote/raw/`. Windows are capped by size: with 36 sensors a half-hour buffer reached
1.5 GB in a 600 MB pod."""

import gzip
import os
import re
import threading
import time
import zlib
from datetime import datetime, timezone
from typing import Optional

from app.core.config.config import settings
from app.core.config.logging import appLogging as log
from app.core.ote.storage import ObjectStorage, get_storage

# `device_id` comes from the URL and ends up in the object key: collapse anything not
# path-safe so a crafted path cannot escape the prefix.
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")

# Worker wake-up interval, not the flush interval (OTE_FLUSH_SECONDS, per device).
_TICK_SECONDS = 5.0

# How much decompressed output to pull per zlib call while enforcing the ceiling.
_INFLATE_CHUNK = 1 * 1024 * 1024


def decompress_bounded(body: bytes, max_output: int) -> Optional[bytes]:
    """Gunzip `body`, giving up as soon as the output would exceed `max_output`.

    SEC-024. `gzip.decompress` inflates the whole stream into memory before
    returning, so the caller cannot react: a ~1 MB body of repeated zeros expands
    to about 1 GB, and 36 sensors posting that concurrently take the pod out.
    The archiver's OTE_MAX_BUFFER_BYTES cap does not help, because it is applied
    to the result, i.e. after the allocation that does the damage.

    Inflating incrementally through `zlib.decompressobj` and checking the running
    total after every chunk bounds the peak allocation at
    `max_output + _INFLATE_CHUNK`, whatever the compression ratio of the input.
    """
    # wbits 16 + MAX_WBITS selects the gzip (RFC 1952) wrapper rather than raw
    # deflate, which is what gzip.decompress accepts.
    decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
    out = bytearray()
    pending = body

    while True:
        out += decompressor.decompress(pending, _INFLATE_CHUNK)
        if len(out) > max_output:
            log.error(
                "OTE archive: gzipped body expands past %d bytes - refusing it "
                "(decompression bomb or misconfigured sensor)", max_output
            )
            return None
        if decompressor.eof:
            break
        pending = decompressor.unconsumed_tail
        if not pending:
            # All input consumed without reaching the end of the gzip stream.
            raise zlib.error("truncated gzip stream")

    return bytes(out)


def sanitize_device_id(device_id: str) -> str:
    return _UNSAFE.sub("_", (device_id or "").strip()).strip("._-") or "unknown"


def decode_body(body: bytes) -> Optional[bytes]:
    """Body -> UTF-8 NDJSON lines, or None if the body is not readable text.

    Order matters: the sensor posts gzipped bodies, and a compressed stream is
    binary, so the 0x0D 0x0A bytes inside it are DATA, not line endings. An
    earlier version normalised newlines first, which deleted those bytes mid
    stream and broke decompression for 598 of 603 real frames. Decompress, then
    decode, and only then treat newlines as separators.

    An unreadable body is dropped (logged, counted in `_undecodable`) instead of
    archived: a .ndjson.gz with corrupt lines mixed in is worse for the ETL than
    a gap it can see in the logs.
    """
    if not body:
        return None
    if body[:2] == b"\x1f\x8b":                       # gzip magic
        try:
            body = decompress_bounded(body, settings.OTE_MAX_DECOMPRESSED_BYTES)
        except Exception as e:
            log.error("OTE archive: body looks gzipped but does not decompress: %s", e)
            return None
        if body is None:
            # Over the ceiling: already logged by decompress_bounded.
            return None
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as e:
        log.error("OTE archive: body is not UTF-8 (%s) — dropped", e)
        return None

    # A body can carry SEVERAL frames separated by newlines (57 of 582 real bodies
    # did), so those newlines are the NDJSON separators and are not collapsed.
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return None
    fragments = [f.strip() for f in text.split("\n") if f.strip()]

    # Unless it is ONE pretty-printed document: told apart without parsing, since
    # every fragment of a batch is a complete object.
    if all(f.startswith("{") and f.endswith("}") for f in fragments):
        return ("\n".join(fragments) + "\n").encode("utf-8")
    return " ".join(text.split()).encode("utf-8") + b"\n"


class RawArchiver:
    def __init__(self, storage: Optional[ObjectStorage] = None,
                 prefix: Optional[str] = None,
                 flush_seconds: Optional[int] = None,
                 flush_max_bytes: Optional[int] = None,
                 max_buffer_bytes: Optional[int] = None):
        self._storage = storage
        self.prefix = (prefix if prefix is not None else settings.OTE_ARCHIVE_PREFIX).strip("/")
        self.flush_seconds = flush_seconds or settings.OTE_FLUSH_SECONDS
        self.flush_max_bytes = flush_max_bytes or settings.OTE_FLUSH_MAX_BYTES
        self.max_buffer_bytes = max_buffer_bytes or settings.OTE_MAX_BUFFER_BYTES

        self._lock = threading.Lock()
        self._lines: dict[str, list[bytes]] = {}
        self._bytes: dict[str, int] = {}
        self._opened_at: dict[str, float] = {}
        self._seq = 0
        self._dropped = 0
        self._archived = 0
        self._undecodable = 0

        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    # ---------------------------------------------------------------- ingest

    def add(self, device_id: str, body: bytes, now: Optional[float] = None) -> None:
        """Queues one frame: called from the request handler, so no parsing and no I/O."""
        line = decode_body(body)
        if line is None:
            self._undecodable += 1
            return
        key = sanitize_device_id(device_id)
        now = time.time() if now is None else now

        with self._lock:
            if key not in self._lines:
                self._lines[key] = []
                self._bytes[key] = 0
                self._opened_at[key] = now
            self._lines[key].append(line)
            self._bytes[key] += len(line)

            # Storage down: drop the oldest instead of growing without bound, loudly.
            while self._bytes[key] > self.max_buffer_bytes and self._lines[key]:
                self._bytes[key] -= len(self._lines[key].pop(0))
                self._dropped += 1
                if self._dropped % 1000 == 1:
                    log.error("OTE archive: buffer for %s over %d bytes — dropping oldest "
                              "frames (%d dropped so far)", key, self.max_buffer_bytes,
                              self._dropped)

    # ----------------------------------------------------------------- flush

    def due_device_ids(self, now: Optional[float] = None) -> list[str]:
        """Devices whose window is closed, by age or by size."""
        now = time.time() if now is None else now
        with self._lock:
            return [
                device_id for device_id, lines in self._lines.items()
                if lines and (now - self._opened_at[device_id] >= self.flush_seconds
                              or self._bytes[device_id] >= self.flush_max_bytes)
            ]

    def flush(self, device_id: str, now: Optional[float] = None) -> Optional[str]:
        """Archives one device's window; None if there was nothing or the upload failed."""
        now = time.time() if now is None else now
        with self._lock:
            lines = self._lines.pop(device_id, None)
            self._bytes.pop(device_id, None)
            opened_at = self._opened_at.pop(device_id, now)
            if not lines:
                return None
            self._seq += 1
            seq = self._seq

        payload = gzip.compress(b"".join(lines))
        key = self._object_key(device_id, opened_at, seq)

        storage = self._resolve_storage()
        if storage is None:
            log.error("OTE archive: no storage configured — discarding %d frames of %s",
                      len(lines), device_id)
            return None
        try:
            storage.put(key, payload)
        except Exception as e:
            # NOT requeued: with storage down that turns into unbounded memory growth.
            log.error("OTE archive: upload of %s failed (%d frames lost): %s", key, len(lines), e)
            return None

        self._archived += len(lines)
        log.info("OTE archive: %s — %d frames, %d bytes gzipped (%d archived in total)",
                 key, len(lines), len(payload), self._archived)
        return key

    def flush_all(self, now: Optional[float] = None) -> list[str]:
        with self._lock:
            device_ids = list(self._lines)
        return [k for k in (self.flush(device_id, now=now) for device_id in device_ids) if k]

    def _object_key(self, device_id: str, opened_at: float, seq: int) -> str:
        """Partitioned by device and UTC day, so the ETL reads one day without listing all.

        The PID is in the key because gunicorn runs TWO workers, each with its own
        `seq` starting at 1; `seq` covers two flushes of one worker in the same ms."""
        stamp = datetime.fromtimestamp(opened_at, tz=timezone.utc)
        return (f"{self.prefix}/{device_id}/{stamp:%Y/%m/%d}/"
                f"{int(opened_at * 1000)}-{os.getpid()}-{seq}.ndjson.gz")

    def _resolve_storage(self) -> Optional[ObjectStorage]:
        """Built on first use: the app must start even with the archive misconfigured."""
        if self._storage is None:
            self._storage = get_storage()
        return self._storage

    # ------------------------------------------------------------- lifecycle

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="ote-archiver", daemon=True)
        self._thread.start()
        log.info("OTE archive: started (window %ds / %d bytes, prefix %r)",
                 self.flush_seconds, self.flush_max_bytes, self.prefix)

    def stop(self, timeout: float = 10.0) -> None:
        """Flushes what is pending, so a controlled restart keeps the current window."""
        self._stop.set()
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(timeout=timeout)
        self.flush_all()

    def _run(self) -> None:
        while not self._stop.wait(_TICK_SECONDS):
            try:
                for device_id in self.due_device_ids():
                    self.flush(device_id)
            except Exception as e:
                # The thread must not die: it is the only thing draining the buffer.
                log.error("OTE archive: flush loop error: %s", e)


# Singleton: start/stop from the app lifespan.
archiver = RawArchiver()


def start() -> None:
    if settings.OTE_ARCHIVE_ENABLED:
        archiver.start()
    else:
        log.info("OTE archive: disabled (OTE_ARCHIVE_ENABLED=false)")


def stop() -> None:
    if settings.OTE_ARCHIVE_ENABLED:
        archiver.stop()
