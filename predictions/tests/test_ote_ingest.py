"""
Tests of the LIDAR raw ingestion (crowd_predictions/etl/ote), over synthetic events.
The cases covered are the ones that fail silently: A->B->A collapsing into A->B, the
overlap of two LIDARs counting one person twice, aforo confused with afluencia, and the
extract losing the first minutes of every window.
"""

import gzip
import json
import os
import shutil
import tempfile
from datetime import datetime, timedelta, timezone

import pandas as pd

from crowd_predictions.config.storage import StorageType
from crowd_predictions.etl.ote.compact_archive import archived_key, compact_archive
from crowd_predictions.etl.ote.etl import OteETL, previous_window, zones_with_lidar
from crowd_predictions.etl.ote.extract import OteExtract
from crowd_predictions.etl.ote.load import OteLoad
from crowd_predictions.etl.ote.transform import (
    census_frame,
    device_metrics,
    new_census,
    presence_segments,
    resolve_label,
    tracks,
    transitions,
    zone_metrics,
)

WINDOW_START = datetime(2026, 8, 11, 11, 0, tzinfo=timezone.utc)
WINDOW_END = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)
WINDOW = (WINDOW_START, WINDOW_END)
GAP = 30.0
# Both fixture device_ids in the same zone, which is what makes the overlap and transit cases
# meaningful.
ZONE_OF_DEVICE = {"A": "Z01", "B": "Z01"}.get


def _event(object_id, seconds, x=0.0, y=0.0, label=None, event_type="OTETrajectoryUpdate"):
    at = WINDOW_START + timedelta(seconds=seconds)
    # The shape of the push, measured over a whole sample: no `sourceId` on the event,
    # and a bare {x, y, z} with no "type". Nothing here is invented.
    event = {
        "type": event_type,
        "timeStamp": int(at.timestamp() * 1000),
        "objectId": object_id,
        "currentLocation": {"x": x, "y": y, "z": 0.9},
        "absorbedObjectIds": [],
        "labels": {},
    }
    if label is not None:
        event["labels"] = {"type": label}
    return event


def _metrics(stream, published_labels=("adult",), stationary_max_m=1.0):
    """The whole chain over a (device_id, event) stream, as the ETL runs it.

    `published_labels` doubles as the priority order (highest first), same as
    OteETL passing ote.label_attrs() for both - one list, not two."""
    labels = list(published_labels)
    segments = presence_segments(stream, GAP, window_end=WINDOW_END)
    track_rows = tracks(segments, labels)
    zones = zone_metrics(track_rows, segments, WINDOW, ZONE_OF_DEVICE,
                         labels, stationary_max_m, label_priority=labels)
    return segments, track_rows, zones


# --- Presence segments and tracks ----------------------------------------------

def test_a_b_a_gives_three_segments_and_the_full_sequence():
    """Why segments are cut: with only first/last sighting per (objectId, device_id) the walk
    collapses into A->B and the way back disappears."""
    stream = (
        [("A", _event("p1", second)) for second in (0, 10)]
        + [("B", _event("p1", second)) for second in (100, 110)]
        + [("A", _event("p1", second)) for second in (200, 210)]
    )

    segments, track_rows, zones = _metrics(stream)

    assert [s["device_id"] for s in segments] == ["A", "B", "A"]
    assert len(track_rows) == 1
    assert [device_id for device_id, _first, _last in track_rows[0]["device_ids"]] == ["A", "B", "A"]
    assert zones["Z01"]["transitions"] == {"A": {"B": 1}, "B": {"A": 1}}
    assert zones["Z01"]["totalTransitions"] == 2


def test_the_same_object_in_two_devices_at_once_is_one_person():
    """Two LIDARs sharing space report the SAME objectId, so counting per sensor and
    adding would duplicate whoever is in the overlap."""
    stream = [("A", _event("p1", second)) for second in (0, 30, 60)] \
        + [("B", _event("p1", second)) for second in (10, 40, 70)]

    segments, track_rows, zones = _metrics(stream)

    assert len(segments) == 2          # one per device_id
    assert len(track_rows) == 1        # one person
    assert zones["Z01"]["totalCount"] == 1
    assert zones["Z01"]["totalConcurrentMax"] == 1


def test_a_track_with_no_idlost_is_closed_by_the_gap():
    """OTEIdLost does not always arrive (4 events for 10 live objects in a sample dump):
    without the gap the stay grows forever and the aforo never comes down."""
    stream = [("A", _event("dies", second)) for second in (0, 10, 20)] \
        + [("A", _event("alive", second)) for second in (3500, 3560, 3595)]

    segments, track_rows, zones = _metrics(stream)

    by_object = {track["object_id"]: track for track in track_rows}
    assert by_object["dies"]["closed"] is True       # silent long before the window ends
    assert by_object["alive"]["closed"] is False     # still being seen at the border
    assert {s["object_id"]: s["closed_reason"] for s in segments} == {"dies": "gap",
                                                                     "alive": "open"}
    # Stay only over CLOSED tracks: the live one is truncated by the border.
    assert zones["Z01"]["totalStayMax"] == 20.0
    assert zones["Z01"]["totalStayAvg"] == 20.0


def test_the_same_id_seen_again_much_later_does_not_bank_the_silence_as_stay():
    """REGRESSION of the case the test above LOOKS like it covers but does not, because it
    uses two different objectIds: cutting into segments was pointless while the track
    still measured last minus first, so 20 s of presence published as 50 minutes."""
    stream = [("A", _event("p1", second)) for second in (0, 10)] \
        + [("A", _event("p1", second)) for second in (3000, 3010)]

    segments, track_rows, zones = _metrics(stream)
    track = track_rows[0]

    assert len(segments) == 2                    # cut by the gap
    assert track["duration_s"] == 3010.0         # the span still holds the silence...
    assert track["presence_s"] == 20.0           # ...but the presence does not
    assert zones["Z01"]["totalStayMax"] == 20.0
    assert zones["Z01"]["totalStayAvg"] == 20.0


def test_the_stay_of_two_overlapping_sensors_is_not_counted_twice():
    """The presence is the UNION of the segments: two LIDARs of one zone see the same
    person at the same time, and adding their segments would double the stay."""
    stream = [("A", _event("p1", second)) for second in (0, 30, 60)] \
        + [("B", _event("p1", second)) for second in (10, 40, 70)]

    _segments, track_rows, zones = _metrics(stream)

    assert track_rows[0]["presence_s"] == 70.0   # 0 -> 70, not 60 + 60
    assert zones["Z01"]["totalStayMax"] == 70.0


def test_idlost_closes_the_segment_even_within_the_gap():
    stream = [("A", _event("p1", 0)), ("A", _event("p1", 5)),
              ("A", _event("p1", 6, event_type="OTEIdLost")),
              ("A", _event("p1", 10))]

    segments, _track_rows, _zones = _metrics(stream)

    assert len(segments) == 2
    assert segments[0]["closed_reason"] == "id_lost"


# --- Movement -------------------------------------------------------------------

def test_a_stationary_object_is_counted_but_never_filtered_out():
    """totalStationaryCount COUNTS, it does not filter, so the threshold can be decided
    later over real data (measured: objects walking 14 and 37 m to end up 10 cm away)."""
    walk = [(0, 0.0, 0.0), (10, 3.0, 0.0), (20, 3.0, 3.0), (30, 0.0, 3.0), (40, 0.1, 0.1)]
    stream = [("A", _event("still", second, x=x, y=y)) for second, x, y in walk]
    stream += [("A", _event("walker", second, x=float(second), y=0.0))
               for second in (0, 10, 20, 30, 40)]

    _segments, track_rows, zones = _metrics(stream)

    still = next(track for track in track_rows if track["object_id"] == "still")
    assert still["path_length_m"] > 11.0            # it did move a lot
    assert still["displacement_m"] < 1.0            # and ended up where it started
    assert zones["Z01"]["totalStationaryCount"] == 1
    assert zones["Z01"]["totalCount"] == 2          # NOT removed from anything else
    assert zones["Z01"]["totalPathLengthAvg"] > 0
    assert zones["Z01"]["totalSpeedAvg"] > 0


# --- Aforo vs afluencia ---------------------------------------------------------

def test_concurrent_max_is_not_the_count():
    """totalCount and totalConcurrentMax are different things: 5 people passing one at a
    time are an afluencia of 5 and an aforo of 1."""
    stream = []
    for index in range(5):
        start = index * 600
        # Every 10 s: further apart than the gap would cut each person in two.
        stream += [("A", _event(f"p{index}", start + offset)) for offset in range(0, 61, 10)]

    _segments, _track_rows, zones = _metrics(stream)

    assert zones["Z01"]["totalCount"] == 5
    assert zones["Z01"]["totalConcurrentMax"] == 1
    # 5 tracks x 60 s present out of a 3600 s window.
    assert zones["Z01"]["totalConcurrentAvg"] == round(300 / 3600, 3)


def test_entered_and_exited_count_the_rotation():
    stream = [("A", _event("early", second)) for second in (0, 10)] \
        + [("A", _event("later", second)) for second in (600, 660)]

    _segments, _track_rows, zones = _metrics(stream)

    # "early" starts on the border: indistinguishable from someone already inside.
    assert zones["Z01"]["totalEntered"] == 1
    assert zones["Z01"]["totalExited"] == 2   # both closed well before the border


# --- Labels ---------------------------------------------------------------------

def test_an_undeclared_label_goes_to_total_and_creates_no_attribute():
    """The importation_job creates attributes from the CSV columns without validating, so
    a new labels.type value would grow an attribute nobody decided."""
    stream = [("A", _event("grown", second, label="adult")) for second in (0, 10)] \
        + [("A", _event("other", second, label="child")) for second in (0, 10)]

    _segments, _track_rows, zones = _metrics(stream)
    attributes = zones["Z01"]

    assert attributes["totalCount"] == 2       # the undeclared one does count here
    assert attributes["adultCount"] == 1
    assert not [key for key in attributes if key.startswith("child")]


def test_every_configured_label_is_emitted_with_zero_when_there_is_none():
    """A sometimes-missing series is a different feature to the model than one worth zero."""
    stream = [("A", _event("grown", second, label="adult")) for second in (0, 10)]

    _segments, _track_rows, zones = _metrics(stream, published_labels=("adult", "child"))

    assert zones["Z01"]["childCount"] == 0
    assert zones["Z01"]["childConcurrentMax"] == 0
    assert zones["Z01"]["childStayP90"] == 0.0


# --- Label priority (a track relabelled mid-sighting) ----------------------------

def test_resolve_label_picks_the_highest_priority_value_present():
    """Unit-level: priority order wins over set order or insertion order."""
    assert resolve_label({"adult", "vehicle"}, ("vehicle", "adult")) == "vehicle"
    assert resolve_label({"adult"}, ("vehicle", "adult")) == "adult"
    assert resolve_label(set(), ("vehicle", "adult")) is None
    # Outside the priority list entirely: still returned (deterministically), not dropped -
    # so _warn_unpublished_labels can still see it and flag it.
    assert resolve_label({"drone"}, ("vehicle", "adult")) == "drone"


def test_resolve_label_with_no_priority_configured_still_returns_something_deterministic():
    """No priority list (the default, and what a caller with nothing configured gets) is
    NOT the same as no labels published - it just means nobody said which one wins, so
    every label seen is "leftover" and the choice falls back to sorted-deterministic."""
    assert resolve_label({"adult", "vehicle"}) == "adult"    # alphabetical, not "vehicle"
    assert resolve_label({"adult"}) == "adult"
    assert resolve_label(set()) is None


def test_a_car_first_read_as_adult_and_then_corrected_ends_up_as_vehicle():
    """The sensor's own failure mode: a car half inside the LIDAR's edge reads small at
    first and corrects itself as more of it comes into view - all within ONE uninterrupted
    sighting, no gap in between. Locking onto the FIRST value (the old behaviour) would
    have kept the wrong early guess forever."""
    stream = [("A", _event("car", 0, label="adult")),
              ("A", _event("car", 10, label="vehicle")),
              ("A", _event("car", 20, label="vehicle"))]

    _segments, track_rows, zones = _metrics(stream, published_labels=("vehicle", "adult"))

    assert track_rows[0]["label"] == "vehicle"
    assert zones["Z01"]["vehicleCount"] == 1
    assert zones["Z01"]["adultCount"] == 0


def test_vehicle_wins_even_if_seen_only_once_against_many_adult_reports():
    """Priority, not a majority vote: one confirmed sighting of the car outweighs every
    earlier misread, however many of those came first."""
    stream = [("A", _event("car", second, label="adult")) for second in range(0, 90, 10)] \
        + [("A", _event("car", 90, label="vehicle"))]

    _segments, track_rows, _zones = _metrics(stream, published_labels=("vehicle", "adult"))

    assert track_rows[0]["label"] == "vehicle"


def test_the_priority_label_wins_even_when_seen_in_a_later_segment_after_a_gap():
    """The correction does not have to land in the same segment - a track split by a gap
    (e.g. it re-enters after a brief silence) still resolves by priority over its FULL
    lifetime, not just its most recent segment."""
    stream = [("A", _event("car", 0, label="adult")), ("A", _event("car", 10, label="adult"))] \
        + [("A", _event("car", 3500, label="vehicle")), ("A", _event("car", 3510, label="vehicle"))]

    segments, track_rows, _zones = _metrics(stream, published_labels=("vehicle", "adult"))

    assert len(segments) == 2                    # still cut by the gap, as before
    assert track_rows[0]["label"] == "vehicle"


def test_a_track_seen_only_as_adult_is_unaffected_by_the_priority_change():
    """No regression: a track never seen as anything else still resolves exactly as
    before - priority only matters once more than one label was ever seen."""
    stream = [("A", _event("p1", second, label="adult")) for second in (0, 10)]

    _segments, track_rows, zones = _metrics(stream, published_labels=("vehicle", "adult"))

    assert track_rows[0]["label"] == "adult"
    assert zones["Z01"]["adultCount"] == 1
    assert zones["Z01"]["vehicleCount"] == 0


def test_a_track_with_no_label_at_all_counts_in_total_only_and_warns_nothing(caplog):
    """No labels.type ever seen (the sensor sent nothing, not an unexpected value) is its
    own case, distinct from an unpublished label: it must count in total*, resolve to
    None, land in no adult*/vehicle* bucket, and NEVER trigger the "unpublished label"
    warning - that warning is for a real value nobody configured, not for "no value"."""
    stream = [("A", _event("no_label", second)) for second in (0, 10)]

    with caplog.at_level("WARNING"):
        _segments, track_rows, zones = _metrics(stream, published_labels=("vehicle", "adult"))

    assert track_rows[0]["label"] is None
    assert zones["Z01"]["totalCount"] == 1
    assert zones["Z01"]["adultCount"] == 0
    assert zones["Z01"]["vehicleCount"] == 0
    assert "not in OTE_LABEL_ATTRS" not in caplog.text


def test_a_zone_with_a_sensor_and_no_data_is_emitted_as_zero():
    zones = zone_metrics([], [], WINDOW, ZONE_OF_DEVICE, ["adult"], 1.0, zone_ids=["Z01"])

    assert zones["Z01"]["totalCount"] == 0
    assert zones["Z01"]["transitions"] == {}
    assert zones["Z01"]["adultStayAvg"] == 0.0


def test_transitions_ignore_the_same_sensor_twice():
    """Device A again after a gap is a re-entry, not a transit."""
    track_rows = [{"device_ids": [("A", None, None), ("A", None, None), ("B", None, None)]}]

    assert transitions(track_rows) == {"A": {"B": 1}}


# --- Device health --------------------------------------------------------------

def _census(frames: list) -> dict:
    """[(offset in seconds, events)] folded, as the extract folds it while streaming."""
    census = new_census()
    for second, events in frames:
        census_frame(census, WINDOW_START + timedelta(seconds=second), events)
    return census


def test_device_metrics_report_rate_empty_ratio_and_silence():
    metrics = device_metrics({"A": _census([(0, 2), (600, 0), (1200, 0)])}, WINDOW)["A"]

    assert metrics["frameRate"] == round(3 / 3600, 3)
    assert metrics["emptyFrameRatio"] == round(2 / 3, 3)
    # The border counts: 2400 s from the last frame to the end, more than any hole.
    assert metrics["silenceMaxSeconds"] == 2400.0
    assert metrics["lastFrameAt"] == "2026-08-11T11:20:00Z"


def test_the_frame_census_is_folded_and_not_a_row_per_frame():
    """a few dozen sensors at 10 fps for an hour is 1.3 M frames: keeping one tuple each was
    ~145 MB. Folded it is two counters plus one run, whatever the number of frames."""
    census = _census([(second, second % 2) for second in range(0, 3600, 10)])

    assert census["frames"] == 360
    assert set(census) == {"frames", "empty", "runs"}
    assert len(census["runs"]) == 1
    assert device_metrics({"A": census}, WINDOW)["A"]["silenceMaxSeconds"] == 10.0


def test_two_overlapping_objects_do_not_invent_silence_between_them():
    """REGRESSION: the gap was measured against the LATEST instant seen, so the frames of
    an overlapping second object went backwards, were dropped as a negative gap, and the
    hole they fill was published as silence - on the entity whose only job is to say
    whether the sensor was alive. Measured: 15 minutes of silence that never happened."""
    first = [(second, 1) for second in list(range(0, 1800, 5)) + list(range(2700, 3600, 5))]
    second_object = [(second, 1) for second in range(1800, 2700, 5)]

    census = _census(first + second_object)          # read A then B, as the reader does
    metrics = device_metrics({"A": census}, WINDOW)["A"]

    assert census["frames"] == 720
    assert len(census["runs"]) == 2                  # the jump backwards opened a run
    assert metrics["silenceMaxSeconds"] == 5.0       # the real cadence, not 905.0


def test_a_sensor_with_no_frames_reports_the_whole_window_as_silence():
    metrics = device_metrics({"A": new_census()}, WINDOW)["A"]

    assert metrics["frameRate"] == 0.0
    assert metrics["silenceMaxSeconds"] == 3600.0
    assert metrics["lastFrameAt"] is None


# --- Extract --------------------------------------------------------------------

class _FakeRawStorage(StorageType):
    """The StorageType contract over an in-memory tree: {key: [lines]}."""

    def __init__(self, files: dict):
        self.files = files

    def upload_file(self, filename: str, path: str) -> str:
        return path

    def download_file(self, filename: str, path: str) -> str:
        with gzip.open(path, "wt", encoding="utf-8") as raw:
            for line in self.files[filename]:
                raw.write(json.dumps(line) + "\n")
        return path

    def delete_file(self, path: str):
        return True


    def list_prefix(self, prefix: str) -> list:
        return sorted(key for key in self.files if key.startswith(prefix))

    def list_subprefixes(self, prefix: str) -> list:
        return sorted({f"{prefix}{key[len(prefix):].split('/')[0]}/"
                       for key in self.files if key.startswith(prefix)})


def _raw_line(seconds, object_ids):
    at = WINDOW_START + timedelta(seconds=seconds)
    return {"timeStamp": int(at.timestamp() * 1000), "sourceId": "TrackingAggregator",
            "events": [_event(object_id, seconds) for object_id in object_ids]}


def _archived(device_id="A", first_seconds=0, last_seconds=None):
    """The key compact_archive writes: YYYYMMDD-HHMMSS-HHMMSS, NOT the receiver's
    `<ms>-<pid>-<seq>`. Built through archived_key so the reader cannot drift from the
    writer again - naming these by hand is what let the extract read 0 events."""
    first = WINDOW_START + timedelta(seconds=first_seconds)
    last = WINDOW_START + timedelta(seconds=first_seconds if last_seconds is None
                                    else last_seconds)
    dumps = [f"ote/incoming/{device_id}/x/{int(moment.timestamp() * 1000)}-1-1.ndjson.gz"
             for moment in (first, last)]
    return archived_key("ote/raw", device_id, dumps)


def test_the_extract_reads_a_file_named_before_the_window():
    """The file name is the START of the dump window, so without the read margin the
    first minutes of every run are lost and NOTHING fails."""
    files = {
        _archived(first_seconds=-300): [
            _raw_line(-60, ["outside"]),   # content before the window: discarded
            _raw_line(120, ["inside"]),    # content inside it: must be read
        ],
    }
    extractor = OteExtract(WINDOW_START, WINDOW_END, storage=_FakeRawStorage(files),
                           margin_seconds=3600, raw_prefix="ote/raw")

    seen = list(extractor.iter_events())

    assert extractor.device_ids() == ["A"]
    assert [event["objectId"] for _device_id, event in seen] == ["inside"]
    # Nor is the earlier frame part of this window's health.
    assert extractor.frames_by_device["A"]["frames"] == 1


def test_the_extract_does_not_filter_by_stage_or_by_event_type():
    """The push API only ever publishes the aggregator. Measured over a whole sample
    of three days: `sourceId` is "TrackingAggregator" in every one, and the only event
    types are OTETrajectoryUpdate and OTEIdLost.

    The lower stages, OTESingleDetection and the JsonResponseWrapper belong to the old
    streaming API, which this deployment does not use, so the filters that dropped them
    were removed: they never fired, and one of them - filtering by the event's `sourceId`,
    which the push format does not carry - once discarded 100% of the real traffic while
    the tests stayed green. Whatever the frame says, its events are read.
    """
    frame = _raw_line(30, ["person"])
    frame["sourceId"] = "una etiqueta que nadie ha visto nunca"
    extractor = OteExtract(WINDOW_START, WINDOW_END, storage=_FakeRawStorage(
        {_archived(): [frame]}), margin_seconds=0, raw_prefix="ote/raw")

    assert [event["objectId"] for _device_id, event in extractor.iter_events()] == ["person"]


def test_an_event_with_no_id_or_no_instant_is_dropped():
    """The only filter left: without an objectId there is nothing to track, and without a
    timeStamp it cannot be placed in a segment."""
    frame = _raw_line(30, ["person"])
    frame["events"] += [{"type": "OTETrajectoryUpdate", "timeStamp": frame["timeStamp"]},
                        {"type": "OTETrajectoryUpdate", "objectId": "sin-hora"}]
    extractor = OteExtract(WINDOW_START, WINDOW_END, storage=_FakeRawStorage(
        {_archived(): [frame]}), margin_seconds=0, raw_prefix="ote/raw")

    assert [event["objectId"] for _device_id, event in extractor.iter_events()] == ["person"]


# --- The whole wiring -----------------------------------------------------------

def test_the_etl_aggregates_two_lidars_of_the_same_zone_and_every_zone_with_a_sensor():
    """End to end over the REAL zone map: L1/L2 are two sensors of Z01, so the person they
    share is one, and a zone with a sensor and no data comes out as a real zero."""
    files = {
        _archived("L1", 0, 20): [_raw_line(second, ["p1"]) for second in (0, 10, 20)],
        _archived("L2", 30, 40): [_raw_line(second, ["p1"]) for second in (30, 40)],
    }
    etl = OteETL(WINDOW_START, WINDOW_END, storage=_FakeRawStorage(files))

    assert etl.extract() is True
    assert etl.transform() is True

    assert etl.zone_metrics["Z01"]["totalCount"] == 1
    assert etl.zone_metrics["Z01"]["transitions"] == {"L1": {"L2": 1}}
    # Z09/Z13/Z15 have no LIDAR: a zero there would be a lie, so they are absent.
    assert "Z09" not in etl.zone_metrics
    assert etl.zone_metrics["Z12"]["totalCount"] == 0
    assert sorted(etl.device_metrics) == ["L1", "L2"]


# --- The window of the entry point ----------------------------------------------

def test_the_previous_window_is_aligned_and_complete():
    """Aligned to the epoch, not "the last hour": consecutive runs must tile the timeline
    without gaps or overlap, and a re-run must land on the same window."""
    now = datetime(2026, 8, 11, 12, 37, 41, tzinfo=timezone.utc)

    window_start, window_end = previous_window(now=now, window_seconds=3600)

    assert (window_start, window_end) == (WINDOW_START, WINDOW_END)
    assert previous_window(now=now + timedelta(minutes=5), window_seconds=3600) == (WINDOW_START,
                                                                                   WINDOW_END)


# --- Load -----------------------------------------------------------------------

def test_load_writes_one_csv_per_entity_named_after_its_urn():
    output_dir = tempfile.mkdtemp()
    try:
        _segments, _track_rows, zones = _metrics(
            [("A", _event("p1", second)) for second in (0, 10)]
            + [("B", _event("p1", second)) for second in (100, 110)])
        devices = device_metrics(
            {"A": _census([(second, 1) for second in range(0, 3600, 60)])}, WINDOW)

        loader = OteLoad(zones, devices, WINDOW_START, output_dir=output_dir)
        files = loader.export_csvs()

        assert len(files) == 2
        zone_csv = next(path for path in files if "LidarZone" in path)
        row = pd.read_csv(zone_csv)
        assert row["urn"].iloc[0] == "urn:ngsi-ld:CrowdFlowLidarZone:Z01"
        assert row["type"].iloc[0] == "CrowdFlowLidarZone"
        # The window START, so a re-run republishes the same sample.
        assert row["timestamp"].iloc[0].startswith("2026-08-11T11:00:00")
        assert json.loads(row["transitions"].iloc[0]) == {"A": {"B": 1}}
        assert os.path.basename(zone_csv) == "urn:ngsi-ld:CrowdFlowLidarZone:Z01.csv"

        device_csv = next(path for path in files if "LidarDevice" in path)
        device_row = pd.read_csv(device_csv)
        assert device_row["urn"].iloc[0] == "urn:ngsi-ld:CrowdFlowLidarDevice:A"
        assert device_row["frameRate"].iloc[0] > 0
        # "serial", the sensor's own id - the one the URL it posts to carries.
        assert device_row["serial"].iloc[0] == "A"
        assert "device_id" not in device_row.columns
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


# --- The seam between the two steps ---------------------------------------------

class _FakeByteStorage(StorageType):
    """Real gzip bytes, so compact_archive and OteExtract can run over the SAME bucket.

    _FakeRawStorage generates the gzip on download, which means no test using it can ever
    see a name it does not like, a broken member or a truncated file.
    """

    def __init__(self, objects=None):
        self.objects = dict(objects or {})

    def upload_file(self, filename, path):
        with open(path, "rb") as handle:
            self.objects[filename] = handle.read()
        return path

    def download_file(self, filename, path):
        with open(path, "wb") as handle:
            handle.write(self.objects[filename])
        return path

    def delete_file(self, path):
        self.objects.pop(path, None)
        return True


    def list_prefix(self, prefix):
        return sorted(key for key in self.objects if key.startswith(prefix))

    def list_subprefixes(self, prefix):
        return sorted({f"{prefix}{key[len(prefix):].split('/')[0]}/"
                       for key in self.objects if key.startswith(prefix)})


def _dump_bytes(*frames):
    return gzip.compress(b"".join(json.dumps(frame).encode() + b"\n" for frame in frames))


def _staged_dump(device_id, seconds, *frames):
    at = WINDOW_START + timedelta(seconds=seconds)
    key = (f"ote/incoming/{device_id}/{at:%Y/%m/%d}/"
           f"{int(at.timestamp() * 1000)}-7-1.ndjson.gz")
    return key, _dump_bytes(*frames)


def test_what_the_compaction_writes_is_what_the_extract_reads():
    """REGRESSION, and the one gap the two-script design creates: extract parsed the
    receiver's `<ms>-<pid>-<seq>` while the compaction had started writing
    `YYYYMMDD-HHMMSS-HHMMSS`, so every archived object was dated 1970 and skipped. Every
    fixture used dump names, so 0 events read looked like a green run of zeros."""
    storage = _FakeByteStorage(dict([
        _staged_dump("A", 60, _raw_line(60, ["p1"]), _raw_line(70, ["p1"])),
        _staged_dump("A", 120, _raw_line(120, ["p1"])),
    ]))

    written = compact_archive(storage, "ote/incoming", "ote/raw", "ote/manifests")
    extractor = OteExtract(WINDOW_START, WINDOW_END, storage=storage, device_ids=["A"],
                           margin_seconds=3600, raw_prefix="ote/raw")

    assert len(written) == 1
    assert [event["objectId"] for _device, event in extractor.iter_events()] == ["p1"] * 3
    assert extractor.frames_by_device["A"]["frames"] == 3


def test_an_object_that_started_before_the_margin_is_still_read():
    """An archived object covers whatever its run found staged, which is unbounded: after
    an outage one object starts hours before the window it still contains. Filtering by
    its START discarded it and published the hour as zeros, data in the bucket."""
    storage = _FakeByteStorage(dict([
        # A run at 13:05 finds three hours of dumps: ONE object, 10:00 -> 12:30.
        _staged_dump("A", -3600, _raw_line(-3000, ["before"])),
        _staged_dump("A", 1800, _raw_line(1800, ["inside"])),
    ]))
    compact_archive(storage, "ote/incoming", "ote/raw", "ote/manifests")
    archived = storage.list_prefix("ote/raw/")[0]

    extractor = OteExtract(WINDOW_START, WINDOW_END, storage=storage, device_ids=["A"],
                           margin_seconds=600, raw_prefix="ote/raw")

    # Its name says it started an hour before a 10-minute margin would allow.
    assert "-100000000-" in archived
    assert [event["objectId"] for _device, event in extractor.iter_events()] == ["inside"]


def test_a_broken_gzip_fails_the_run_instead_of_publishing_a_hole():
    """A member broken in the MIDDLE loses every member after it, and Timescale ingests
    with ON CONFLICT DO NOTHING, so a partial hour published in green is permanent."""
    key = _archived(first_seconds=0, last_seconds=60)
    storage = _FakeByteStorage({key: _dump_bytes(_raw_line(0, ["p1"])) + b"\x1f\x8b broken"})
    etl = OteETL(WINDOW_START, WINDOW_END, storage=storage)
    etl.device_ids = ["A"]

    assert etl.extract() is True
    assert etl.transform() is True
    assert etl.extractor.unreadable == [key]
    assert etl._window_is_trustworthy() is False


def test_a_window_with_no_frames_at_all_is_not_a_quiet_hour():
    """Zeros for every zone are indistinguishable from a bad prefix or bad credentials,
    and cannot be corrected later, so the run has to go red."""
    etl = OteETL(WINDOW_START, WINDOW_END, storage=_FakeByteStorage())

    assert etl.extract() is True
    assert etl.transform() is True
    assert etl._window_is_trustworthy() is False


# --- Per-target isolation -------------------------------------------------------

def test_a_target_only_publishes_the_zones_of_its_own_sensors():
    """ZONES is global and hardcoded: without this every tenant published every other
    tenant's zones, so a second target created TenantA zones inside its own scope."""
    everything = zones_with_lidar()
    just_one = zones_with_lidar(["L1"])

    assert len(just_one) == 1
    assert set(just_one).issubset(everything)
    # No declared device ids means "every sensor", the single-tenant install.
    assert zones_with_lidar([]) == everything


# --- Out-of-order events, i.e. archived objects that overlap ---------------------

def test_events_arriving_out_of_order_never_produce_negative_metrics():
    """REGRESSION. Two archived objects of one device overlap as soon as a dump lands
    mid-run - which the compaction supports on purpose - so the stream is NOT strictly
    chronological. `last_seen = seen_at` then went backwards past the gap check and
    published a negative stay and a negative aforo, in green."""
    stream = [("A", _event("p1", second)) for second in (0, 30, 2400, 2430, 1200, 1230)]

    segments, track_rows, zones = _metrics(stream)

    assert all(segment["duration_s"] >= 0 for segment in segments)
    assert all(track["presence_s"] >= 0 for track in track_rows)
    assert zones["Z01"]["totalStayMax"] >= 0
    assert zones["Z01"]["totalConcurrentAvg"] >= 0
    # 3 sightings x 30 s of presence, NOT the 2430 s the span would have given.
    assert zones["Z01"]["totalStayMax"] == 90.0


def test_an_out_of_order_event_inside_the_segment_extends_it_instead_of_cutting_it():
    stream = [("A", _event("p1", 0)), ("A", _event("p1", 20)), ("A", _event("p1", 10))]

    segments, _track_rows, _zones = _metrics(stream)

    assert len(segments) == 1
    assert segments[0]["duration_s"] == 20.0
    assert segments[0]["n_frames"] == 3


def test_the_same_objectid_in_two_zones_does_not_mix_their_metrics():
    """REGRESSION: `_metric_block` read the GLOBAL track, which aggregates every zone the
    objectId was seen in, so a person crossing Z01 and Z03 published each zone's stay,
    path and displacement in BOTH."""
    zone_of = {"L1": "Z01", "L9": "Z03"}.get
    stream = [("L1", _event("p1", second)) for second in (0, 10, 20)] \
        + [("L9", _event("p1", second)) for second in (25, 35)]

    segments = presence_segments(stream, GAP, window_end=WINDOW_END)
    zones = zone_metrics(tracks(segments), segments, WINDOW, zone_of, ["adult"], 1.0,
                         zone_ids=["Z01", "Z03"])

    assert zones["Z01"]["totalStayMax"] == 20.0     # 0 -> 20 in L1
    assert zones["Z03"]["totalStayMax"] == 10.0     # 25 -> 35 in L9
    # And one person in each: the count still deduplicates within the zone.
    assert zones["Z01"]["totalCount"] == zones["Z03"]["totalCount"] == 1


def test_a_zone_with_no_transit_of_its_own_reports_none():
    """Transits are rebuilt from the zone's segments, so the sensors of another zone
    cannot appear in this one's matrix."""
    zone_of = {"L1": "Z01", "L9": "Z03"}.get
    stream = [("L1", _event("p1", second)) for second in (0, 10)] \
        + [("L9", _event("p1", second)) for second in (20, 30)]

    segments = presence_segments(stream, GAP, window_end=WINDOW_END)
    zones = zone_metrics(tracks(segments), segments, WINDOW, zone_of, ["adult"], 1.0,
                         zone_ids=["Z01", "Z03"])

    assert zones["Z01"]["transitions"] == {}
    assert zones["Z03"]["totalTransitions"] == 0


# --- What is published when the window cannot be believed ------------------------

def test_an_untrustworthy_window_publishes_the_sensors_but_NOT_the_zones():
    """The asymmetry is the point: a zone zero is what feeds the model and Timescale
    ingests it with ON CONFLICT DO NOTHING, so publishing it and then going red leaves the
    bad sample for good. The device entities are the signal that says what went wrong."""
    output_dir = tempfile.mkdtemp()
    try:
        # L1, which IS in zones_config, so the zone metrics do exist and are withheld.
        key = _archived("L1", 0, 60)
        storage = _FakeByteStorage({key: _dump_bytes(_raw_line(0, ["p1"])) + b"\x1f\x8b roto"})
        etl = OteETL(WINDOW_START, WINDOW_END, storage=storage, output_dir=output_dir)
        etl.device_ids = ["L1"]
        etl.extract()
        etl.transform()

        assert etl.zone_metrics                      # they were computed...
        assert etl._window_is_trustworthy() is False
        assert etl.load() is False
        written = [os.path.basename(path) for path in etl.loader.exported_files]

        # ...and none of them was written: only the sensor, which is the alarm.
        assert written == ["urn:ngsi-ld:CrowdFlowLidarDevice:L1.csv"]
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_device_ids_that_are_in_no_zone_are_not_a_green_run():
    """The device id comes from the URL the sensor is configured with, so it does not have
    to match any lidar_ids of zones_config. When it does not, the run published sensor
    health, zero zone metrics and exit 0.

    A deliberately unknown id, NOT a real one: which sensors map to a zone is a local
    decision - the test LIDAR gets its own zone in a working tree that is not committed -
    so a test naming a real id would pass or fail depending on who runs it.
    """
    unmapped = "sensor-sin-zona"
    storage = _FakeByteStorage(dict([_staged_dump(unmapped, 60, _raw_line(60, ["p1"]))]))
    compact_archive(storage, "ote/incoming", "ote/raw", "ote/manifests")
    etl = OteETL(WINDOW_START, WINDOW_END, storage=storage)
    etl.device_ids = [unmapped]

    etl.extract()
    etl.transform()

    assert etl.device_metrics[unmapped]["lastFrameAt"] is not None   # it did report
    assert etl.zone_metrics == {}                            # and no zone claims it
    assert etl._window_is_trustworthy() is False
