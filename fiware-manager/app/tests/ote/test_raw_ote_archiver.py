import gzip
import json
import os

import pytest

from app.core.ote.raw_ote_archiver import RawArchiver, decode_body, sanitize_device_id


class FakeStorage:
    """Records the puts instead of talking to S3/Minio."""

    def __init__(self, fail: bool = False):
        self.objects: dict[str, bytes] = {}
        self.fail = fail

    def put(self, key: str, data: bytes) -> None:
        if self.fail:
            raise RuntimeError("storage down")
        self.objects[key] = data


@pytest.fixture
def storage() -> FakeStorage:
    return FakeStorage()


@pytest.fixture
def archiver(storage) -> RawArchiver:
    return RawArchiver(storage=storage, prefix="ote/raw", flush_seconds=60,
                       flush_max_bytes=1_000_000, max_buffer_bytes=10_000_000)


FRAME = b'{"type":"JsonResponseWrapper","content":{"type":"ObjectTrackingEvents","events":[]}}'


class TestBodyDecoding:
    """REGRESSION: normalising newlines before decompressing the GZIPPED bodies
    destroyed 598 of 603 frames."""

    def test_gzipped_body_is_decompressed(self):
        assert decode_body(gzip.compress(FRAME)) == FRAME + b"\n"

    def test_plain_body_passes_through(self):
        assert decode_body(FRAME) == FRAME + b"\n"

    def test_gzipped_body_survives_a_round_trip(self, archiver, storage):
        archiver.add("lib-01", gzip.compress(FRAME))
        key = archiver.flush("lib-01")
        line = gzip.decompress(storage.objects[key]).decode().strip()
        assert json.loads(line)["type"] == "JsonResponseWrapper"

    def test_bytes_that_are_not_text_are_dropped_not_stored(self, archiver, storage):
        archiver.add("lib-01", b"\xff\xfe\x00binario")
        assert archiver.flush("lib-01") is None
        assert storage.objects == {}

    def test_truncated_gzip_is_dropped(self, archiver, storage):
        archiver.add("lib-01", gzip.compress(FRAME)[:20])
        assert archiver.flush("lib-01") is None
        assert storage.objects == {}

    def test_empty_body_is_ignored(self, archiver):
        archiver.add("lib-01", b"")
        assert archiver.flush("lib-01") is None

    def test_a_batched_body_becomes_one_line_per_frame(self):
        # 57 of 582 real bodies carried more than one frame: the newlines separate them.
        body = b'{"timeStamp":1}\n{"timeStamp":2}\n{"timeStamp":3}\n'
        assert decode_body(body) == b'{"timeStamp":1}\n{"timeStamp":2}\n{"timeStamp":3}\n'

    def test_a_pretty_printed_frame_is_not_split(self):
        assert decode_body(b'{\n  "a": 1\n}') == b'{ "a": 1 }\n'

    def test_a_batch_survives_the_round_trip_as_ndjson(self, archiver, storage):
        archiver.add("lib-01", gzip.compress(b'{"a":1}\n{"a":2}'))
        key = archiver.flush("lib-01")
        lines = gzip.decompress(storage.objects[key]).decode().splitlines()
        assert [json.loads(ln)["a"] for ln in lines] == [1, 2]


class TestArchivedContent:
    def test_frames_are_stored_verbatim_one_per_line(self, archiver, storage):
        archiver.add("lib-01", FRAME)
        archiver.add("lib-01", FRAME)
        key = archiver.flush("lib-01")

        lines = gzip.decompress(storage.objects[key]).decode().splitlines()
        assert lines == [FRAME.decode(), FRAME.decode()]
        # Still parseable as NDJSON, which is what the ETL reads.
        assert all(json.loads(line)["type"] == "JsonResponseWrapper" for line in lines)

    def test_embedded_newlines_do_not_break_the_ndjson(self, archiver, storage):
        archiver.add("lib-01", b'{"a":\n1}')
        key = archiver.flush("lib-01")
        assert gzip.decompress(storage.objects[key]) == b'{"a": 1}\n'

    def test_flush_without_data_is_a_noop(self, archiver):
        assert archiver.flush("never-seen") is None


class TestObjectKey:
    def test_partitioned_by_device_and_utc_day(self, archiver, storage):
        archiver.add("lib-01", FRAME, now=1786089350.353)
        key = archiver.flush("lib-01")
        # 1786089350.353 = 2026-08-07 07:55:50 UTC
        assert key == f"ote/raw/lib-01/2026/08/07/1786089350353-{os.getpid()}-1.ndjson.gz"

    def test_a_whole_day_lands_in_one_folder(self, archiver, storage):
        morning = 1786089350.353            # 2026-08-07 07:55:50 UTC
        evening = morning + 14 * 3600       # 21:55:50, same UTC day
        archiver.add("lib-01", FRAME, now=morning)
        first = archiver.flush("lib-01")
        archiver.add("lib-01", FRAME, now=evening)
        last = archiver.flush("lib-01")
        assert first.rsplit("/", 1)[0] == last.rsplit("/", 1)[0] == "ote/raw/lib-01/2026/08/07"

    def test_two_flushes_in_the_same_second_do_not_collide(self, archiver, storage):
        archiver.add("a", FRAME, now=1786089350.353)
        first = archiver.flush("a")
        archiver.add("a", FRAME, now=1786089350.353)
        second = archiver.flush("a")
        assert first != second
        assert len(storage.objects) == 2

    def test_each_device_gets_its_own_object(self, archiver, storage):
        archiver.add("lib-01", FRAME)
        archiver.add("lib-02", FRAME)
        keys = [archiver.flush("lib-01"), archiver.flush("lib-02")]
        assert "/lib-01/" in keys[0] and "/lib-02/" in keys[1]


class TestDeviceIdSanitising:
    @pytest.mark.parametrize("raw,expected", [
        ("lib-01", "lib-01"),
        ("../../etc/passwd", "etc_passwd"),
        ("gijon z12", "gijon_z12"),
        ("", "unknown"),
        ("///", "unknown"),
    ])
    def test_device_id_cannot_escape_the_prefix(self, raw, expected):
        assert sanitize_device_id(raw) == expected

    def test_sanitised_device_id_is_used_in_the_key(self, archiver):
        archiver.add("../../secret", FRAME)
        key = archiver.flush("secret")
        assert key is not None and ".." not in key


class TestFlushTriggers:
    def test_window_is_due_by_age(self, archiver):
        archiver.add("lib-01", FRAME, now=1000.0)
        assert archiver.due_device_ids(now=1059.0) == []
        assert archiver.due_device_ids(now=1060.0) == ["lib-01"]

    def test_window_is_due_by_size(self, storage):
        archiver = RawArchiver(storage=storage, flush_seconds=3600, flush_max_bytes=100,
                              max_buffer_bytes=10_000)
        archiver.add("lib-01", b"x" * 50, now=1000.0)
        assert archiver.due_device_ids(now=1000.0) == []
        archiver.add("lib-01", b"x" * 60, now=1000.0)
        assert archiver.due_device_ids(now=1000.0) == ["lib-01"]

    def test_flush_all_drains_every_device(self, archiver, storage):
        archiver.add("a", FRAME)
        archiver.add("b", FRAME)
        assert len(archiver.flush_all()) == 2
        # Nothing left behind: a second flush of the same devices has nothing to write.
        assert archiver.flush_all() == []


class TestFailureModes:
    def test_upload_failure_loses_the_window_but_not_the_process(self):
        archiver = RawArchiver(storage=FakeStorage(fail=True))
        archiver.add("lib-01", FRAME)
        assert archiver.flush("lib-01") is None
        # The window is gone, and the buffer with it: no retry, no growth.
        assert archiver.flush("lib-01") is None

    def test_buffer_is_capped_dropping_the_oldest(self, storage):
        archiver = RawArchiver(storage=storage, flush_seconds=3600,
                               flush_max_bytes=10_000_000, max_buffer_bytes=300)
        for i in range(100):
            archiver.add("lib-01", b"%03d" % i)  # 4 bytes each with the newline

        key = archiver.flush("lib-01")
        kept = gzip.decompress(storage.objects[key]).decode().splitlines()
        # Capped at 300 bytes / 4 bytes per frame: the oldest ones are gone...
        assert len(kept) <= 300 // 4
        # ...and what survives is the tail, the most recent frames.
        assert kept[-1] == "099"
