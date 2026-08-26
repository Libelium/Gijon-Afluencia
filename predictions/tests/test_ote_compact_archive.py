import gzip
import json
import time
from datetime import datetime, timezone

import pytest

from crowd_predictions.config.storage import StorageType
from crowd_predictions.etl.ote.compact_archive import (
    MANIFEST_SUFFIX,
    CompactionIncomplete,
    archive_interval,
    archived_key,
    manifest_key,
    compact_archive,
    dump_timestamp,
    pending_by_device,
    recover,
)

# 2026-08-11 13:02:00 UTC and 13:09:00 UTC
# Manifests live in their OWN prefix: recover() lists it on every run.
MANIFESTS = "ote/manifests"
MS_1302 = 1786453320000
MS_1309 = 1786453740000


class FakeStorage(StorageType):
    """In-memory bucket; `fail_upload_of` corrupts one key to exercise the validation."""

    def __init__(self, objects=None, fail_upload_of=None):
        self.objects = dict(objects or {})
        self.fail_upload_of = fail_upload_of
        self.deleted = []

    def upload_file(self, filename, path):
        with open(path, "rb") as handle:
            body = handle.read()
        # A truncated upload, which is the realistic failure.
        self.objects[filename] = body[:-1] if filename == self.fail_upload_of else body
        return path

    def download_file(self, filename, path):
        with open(path, "wb") as handle:
            handle.write(self.objects[filename])
        return path

    def delete_file(self, path):
        self.deleted.append(path)
        self.objects.pop(path, None)
        return True


    def list_prefix(self, prefix):
        return sorted(key for key in self.objects if key.startswith(prefix))

    def list_subprefixes(self, prefix):
        # The compaction never discovers devices by listing, but the contract requires it.
        return sorted({f"{prefix}{key[len(prefix):].split('/')[0]}/"
                       for key in self.objects if key.startswith(prefix)})


def _dump(*frames):
    return gzip.compress(b"".join(json.dumps(f).encode() + b"\n" for f in frames))


def _staged(device_id="lib-01"):
    return {
        f"ote/incoming/{device_id}/2026/08/11/{MS_1302}-7-1.ndjson.gz": _dump({"n": 1}, {"n": 2}),
        f"ote/incoming/{device_id}/2026/08/11/{MS_1309}-8-1.ndjson.gz": _dump({"n": 3}),
    }


class TestPending:
    def test_groups_by_device_in_chronological_order(self):
        objects = {**_staged("lib-01"), **_staged("lib-02")}
        pending = pending_by_device(FakeStorage(objects), "ote/incoming")

        assert sorted(pending) == ["lib-01", "lib-02"]
        assert [dump_timestamp(k).strftime("%H:%M") for k in pending["lib-01"]] == ["13:02", "13:09"]

    def test_ignores_names_that_are_not_dumps(self):
        objects = {**_staged(), "ote/incoming/lib-01/2026/08/11/algo.txt": b"x"}
        assert len(pending_by_device(FakeStorage(objects), "ote/incoming")["lib-01"]) == 2


class TestName:
    def test_states_the_interval_it_really_covers(self):
        keys = sorted(_staged())
        assert archived_key("ote/raw", "lib-01", keys) == (
            "ote/raw/lib-01/2026/08/11/20260811-130200000-130900000.ndjson.gz")

    def test_the_name_is_to_the_millisecond_so_two_runs_cannot_overwrite_each_other(self):
        """A late dump compacted on its own produced the same key as the previous run and
        silently replaced it, sources already deleted. At second resolution it still could:
        the receiver runs two workers, so two dumps of one device share a second."""
        first_run = sorted(_staged())
        same_second = f"ote/incoming/lib-01/2026/08/11/{MS_1302 + 300}-8-1.ndjson.gz"

        assert archived_key("ote/raw", "lib-01", [same_second]) != archived_key(
            "ote/raw", "lib-01", [f"ote/incoming/lib-01/2026/08/11/{MS_1302}-7-1.ndjson.gz"])
        assert archived_key("ote/raw", "lib-01", [same_second]) != archived_key(
            "ote/raw", "lib-01", first_run)

    def test_an_object_never_spans_more_than_a_clock_hour(self):
        """The ingestion reads by clock hour, so an object covering more is downloaded and
        re-read WHOLE by every run overlapping it: after a day of backlog each of the 24
        catch-up runs re-read the entire day. The name could not describe more than 24 h
        either, so an outage of days made the whole archive invisible."""
        backlog = {
            # Two days earlier, and two different hours of the staged day.
            f"ote/incoming/lib-01/2026/08/09/{MS_1302 - 2 * 86400000}-7-1.ndjson.gz": _dump({"n": 1}),
            f"ote/incoming/lib-01/2026/08/11/{MS_1302 - 3600000}-7-2.ndjson.gz": _dump({"n": 2}),
            **_staged("lib-01"),
        }
        storage = FakeStorage(backlog)

        written = compact_archive(storage, "ote/incoming", "ote/raw", MANIFESTS)

        assert len(written) == 3                           # one per clock hour, not one for all
        for key in written:
            start, end = archive_interval(key)
            assert start.replace(minute=0, second=0, microsecond=0) == \
                   end.replace(minute=0, second=0, microsecond=0)
        assert storage.list_prefix("ote/incoming/") == []   # and the area is still emptied

    def test_two_runs_in_the_same_hour_write_two_objects(self):
        """The cap is a CEILING on the span, not a schedule: each run archives whatever it
        found, so the hourly CronJob keeps producing one object per run."""
        storage = FakeStorage(_staged())
        first = compact_archive(storage, "ote/incoming", "ote/raw", MANIFESTS)

        storage.objects[f"ote/incoming/lib-01/2026/08/11/{MS_1302 + 120000}-7-3.ndjson.gz"] = \
            _dump({"n": 4})
        second = compact_archive(storage, "ote/incoming", "ote/raw", MANIFESTS)

        assert len(first) == len(second) == 1
        assert first != second                             # different names, no overwrite
        assert len(storage.list_prefix("ote/raw/")) == 2

    def test_the_interval_is_read_back_from_the_name(self):
        """The reader parses this, so writer and reader must not drift: parsing it in
        extract.py on its own is what made it read 0 events."""
        key = archived_key("ote/raw", "lib-01", sorted(_staged()))

        assert archive_interval(key) == (datetime(2026, 8, 11, 13, 2, tzinfo=timezone.utc),
                                        datetime(2026, 8, 11, 13, 9, tzinfo=timezone.utc))

    @pytest.mark.parametrize("name", [
        "20260811-130200000-130900000.ndjson.gz.manifest.json",   # would be read as data
        f"{MS_1302}-7-1.ndjson.gz",                          # a receiver dump
        "algo.txt",
    ])
    def test_only_archived_names_are_data(self, name):
        assert archive_interval(f"ote/raw/lib-01/2026/08/11/{name}") is None

    def test_an_interval_that_goes_backwards_is_not_data(self):
        """An object never spans more than a clock hour, let alone midnight, so this can
        only be a name written before that rule - and read backwards it gives negatives."""
        assert archive_interval(
            "ote/raw/x/2026/08/11/20260811-235900000-000500000.ndjson.gz") is None


class TestConsolidate:
    def test_joins_the_dumps_and_empties_the_staging_area(self):
        storage = FakeStorage(_staged())
        written = compact_archive(storage, "ote/incoming", "ote/raw", MANIFESTS)

        assert written == ["ote/raw/lib-01/2026/08/11/20260811-130200000-130900000.ndjson.gz"]
        lines = gzip.decompress(storage.objects[written[0]]).decode().splitlines()
        assert [json.loads(line)["n"] for line in lines] == [1, 2, 3]
        assert storage.list_prefix("ote/incoming/") == []

    def test_the_manifest_is_removed_when_it_finishes(self):
        """Its existence is the state: while it is there, the run is unfinished."""
        storage = FakeStorage(_staged())
        compact_archive(storage, "ote/incoming", "ote/raw", MANIFESTS)
        assert [k for k in storage.objects if k.endswith(MANIFEST_SUFFIX)] == []

    def test_a_device_failing_does_not_stop_the_others_but_does_fail_the_run(self):
        """Both halves matter: lib-02 must be compacted, and the run must still come out
        red, or the ingestion would publish a window missing lib-01 and look green."""
        objects = {**_staged("lib-01"), **_staged("lib-02")}
        broken = "ote/raw/lib-01/2026/08/11/20260811-130200000-130900000.ndjson.gz"
        storage = FakeStorage(objects, fail_upload_of=broken)

        with pytest.raises(CompactionIncomplete) as raised:
            compact_archive(storage, "ote/incoming", "ote/raw", MANIFESTS)

        assert raised.value.failed == ["lib-01"]
        assert raised.value.written == [
            "ote/raw/lib-02/2026/08/11/20260811-130200000-130900000.ndjson.gz"]
        # Its sources stay staged for the next run...
        assert len(storage.list_prefix("ote/incoming/lib-01/")) == 2
        # ...and the corrupt object and its manifest are gone: a manifest left behind
        # would make recover() delete those sources without ever re-reading the object.
        assert broken not in storage.objects
        assert [k for k in storage.objects if k.endswith(MANIFEST_SUFFIX)] == []

    def test_deletes_by_explicit_list_not_by_prefix(self):
        """A dump landing mid-run must survive to the next run: deleting by prefix would
        take it away unprocessed and it would be lost for good."""
        late = f"ote/incoming/lib-01/2026/08/11/{MS_1309 + 60000}-7-2.ndjson.gz"

        class ArrivesMidRun(FakeStorage):
            """Injects the late dump on the first download, i.e. after the listing."""

            def download_file(self, filename, path):
                self.objects.setdefault(late, _dump({"n": 99}))
                return super().download_file(filename, path)

        storage = ArrivesMidRun(_staged())
        staged_before = sorted(storage.list_prefix("ote/incoming/"))

        compact_archive(storage, "ote/incoming", "ote/raw", MANIFESTS)

        # The two it listed are gone; the one that arrived after is untouched.
        assert set(staged_before).issubset(set(storage.deleted))
        assert storage.list_prefix("ote/incoming/") == [late]


ARCHIVED_KEY = "ote/raw/lib-01/2026/08/11/20260811-130200000-130900000.ndjson.gz"


def _died_before_deleting(storage, body: bytes, declared_bytes: int = None):
    """The one state recover() exists for: object uploaded, manifest written, dumps not
    yet deleted. `declared_bytes` lies about the size to simulate a truncated upload."""
    storage.objects[ARCHIVED_KEY] = body
    storage.objects[manifest_key(MANIFESTS, ARCHIVED_KEY)] = json.dumps(
        {"archived": ARCHIVED_KEY,
         "bytes": len(body) if declared_bytes is None else declared_bytes,
         "sources": sorted(_staged())}).encode()


class TestRecover:
    def test_finishes_a_run_that_died_before_deleting(self):
        storage = FakeStorage(_staged())
        _died_before_deleting(storage, _dump({"n": 1}, {"n": 2}) + _dump({"n": 3}))

        assert recover(storage, MANIFESTS) == 1
        # Sources gone: otherwise the next run would compact them again, duplicating
        # the frames in a second object.
        assert storage.list_prefix("ote/incoming/") == []
        assert manifest_key(MANIFESTS, ARCHIVED_KEY) not in storage.objects
        assert ARCHIVED_KEY in storage.objects

    def test_never_deletes_the_dumps_of_an_object_it_cannot_verify(self):
        """The irreversible mistake of the whole chain. The manifest only proves the run
        died, not that the upload was good: trusting it deleted the only surviving copy
        of the hour and left a corrupt object in its place."""
        storage = FakeStorage(_staged())
        _died_before_deleting(storage, b"not a gzip at all")

        assert recover(storage, MANIFESTS) == 0
        assert len(storage.list_prefix("ote/incoming/")) == 2      # the raw data survives
        assert ARCHIVED_KEY not in storage.objects                 # the garbage does not
        assert manifest_key(MANIFESTS, ARCHIVED_KEY) not in storage.objects

    def test_a_truncated_upload_is_caught_by_the_size_even_if_the_gzip_opens(self):
        """A gzip cut on a member boundary still decompresses: only the byte count the
        manifest recorded says it is short."""
        storage = FakeStorage(_staged())
        _died_before_deleting(storage, _dump({"n": 1}),
                              declared_bytes=len(_dump({"n": 1})) + 500)

        assert recover(storage, MANIFESTS) == 0
        assert len(storage.list_prefix("ote/incoming/")) == 2

    def test_does_nothing_when_there_is_no_manifest(self):
        storage = FakeStorage(_staged())
        assert recover(storage, MANIFESTS) == 0
        assert len(storage.list_prefix("ote/incoming/")) == 2


class TestGzipConcatenation:
    def test_joined_members_read_as_one_stream(self):
        """The property the design rests on: gzip admits concatenated members, so joining
        is a byte operation with no decompressing."""
        joined = _dump({"n": 1}) + _dump({"n": 2}) + _dump({"n": 3})
        lines = gzip.decompress(joined).decode().splitlines()
        assert [json.loads(line)["n"] for line in lines] == [1, 2, 3]


class TestAbruptDeath:
    """The manifest is written BEFORE the object, so no moment of death leaves a state
    recover() cannot resolve. The other order had one, and it duplicated frames for ever.

    Killed with SystemExit because a SIGKILL is not an Exception either: nothing the code
    catches gets a chance to run, which is the whole point.
    """

    @staticmethod
    def _kill_after_uploading(storage, data: bool):
        """Kills right after the upload of the DATA object (data=True) or of the manifest."""
        original = storage.upload_file

        def suicide(key, path):
            result = original(key, path)
            if key.endswith(MANIFEST_SUFFIX) is not data:
                raise SystemExit(f"killed right after uploading {key}")
            return result
        storage.upload_file = suicide

    def test_dying_right_after_uploading_the_object_archives_it_exactly_once(self):
        """REGRESSION. With the object uploaded FIRST, a kill before the manifest left it
        with a valid DATA name, no manifest (so recover() never saw it) and its dumps still
        staged: the next run archived them again under a different name and the same frames
        stayed in the archive twice, uncorrectable."""
        storage = FakeStorage(_staged())
        self._kill_after_uploading(storage, data=True)

        with pytest.raises(SystemExit):
            compact_archive(storage, "ote/incoming", "ote/raw", MANIFESTS)

        # The manifest is already there, so recover() can resolve it either way.
        assert [k for k in storage.objects if k.endswith(MANIFEST_SUFFIX)] == [
            manifest_key(MANIFESTS, ARCHIVED_KEY)]
        assert len(storage.list_prefix("ote/incoming/")) == 2       # nothing deleted yet

        storage.upload_file = FakeStorage.upload_file.__get__(storage)
        assert recover(storage, MANIFESTS) == 1                    # the object was intact
        assert storage.list_prefix("ote/incoming/") == []          # so the dumps go
        archived = storage.list_prefix("ote/raw/")
        assert archived == [ARCHIVED_KEY]                          # ONE object, not two
        lines = gzip.decompress(storage.objects[archived[0]]).decode().splitlines()
        assert [json.loads(line)["n"] for line in lines] == [1, 2, 3]

    def test_dying_right_after_the_manifest_keeps_the_dumps(self):
        """The manifest exists and the object does not: recover() must not read that as
        "already archived" and delete the only surviving copy."""
        storage = FakeStorage(_staged())
        self._kill_after_uploading(storage, data=False)

        with pytest.raises(SystemExit):
            compact_archive(storage, "ote/incoming", "ote/raw", MANIFESTS)

        storage.upload_file = FakeStorage.upload_file.__get__(storage)
        assert recover(storage, MANIFESTS) == 0
        assert len(storage.list_prefix("ote/incoming/")) == 2
        assert [k for k in storage.objects if k.endswith(MANIFEST_SUFFIX)] == []
        assert storage.list_prefix("ote/raw/") == []


class TestThroughput:
    """The cost of a run is round trips, not bytes: gzip concatenation is 0.8 ms per
    sensor-hour, and one DELETE per dump plus one sequential GET per dump was the rest."""

    def test_the_sources_are_deleted_in_one_batch(self):
        deleted_in_batches = []

        class BatchStorage(FakeStorage):
            def delete_files(self, keys):
                deleted_in_batches.append(list(keys))
                for key in keys:
                    self.objects.pop(key, None)

        storage = BatchStorage(_staged())
        compact_archive(storage, "ote/incoming", "ote/raw", MANIFESTS)

        assert deleted_in_batches == [sorted(_staged())]      # ONE call, both dumps
        assert storage.list_prefix("ote/incoming/") == []

    def test_a_backend_without_batch_delete_still_works(self):
        """The contract's default loops, so any other backend keeps working unchanged."""
        storage = FakeStorage(_staged())          # only implements delete_file
        compact_archive(storage, "ote/incoming", "ote/raw", MANIFESTS)

        assert storage.list_prefix("ote/incoming/") == []
        assert sorted(storage.deleted)[:2] == sorted(_staged())

    def test_downloading_in_parallel_keeps_the_dumps_in_order(self):
        """The gap logic of presence_segments() reads the stream as chronological, so the
        parts must be concatenated in order however the downloads finish."""
        many = {f"ote/incoming/lib-01/2026/08/11/{MS_1302 + n * 1000}-7-{n}.ndjson.gz":
                _dump({"n": n}) for n in range(20)}

        class ReversedFinish(FakeStorage):
            """The FIRST keys answer last, so completion order is the reverse of the list.
            Without a real inversion this test passes whatever the code does."""

            def download_file(self, filename, path):
                if filename.startswith("ote/incoming/"):    # not the verification re-read
                    index = int(filename.rsplit("-", 1)[-1].split(".")[0])
                    time.sleep((20 - index) * 0.002)
                return super().download_file(filename, path)

        storage = ReversedFinish(many)
        written = compact_archive(storage, "ote/incoming", "ote/raw", MANIFESTS, workers=8)

        lines = gzip.decompress(storage.objects[written[0]]).decode().splitlines()
        assert [json.loads(line)["n"] for line in lines] == list(range(20))
