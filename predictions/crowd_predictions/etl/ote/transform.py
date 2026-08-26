"""Raw OTE events -> the entities of ote_etl_datamodel.md. Pure functions.

Cut into PRESENCE SEGMENTS, `(objectId, device_id)` per silence: with only first/last
sighting, A->B->A collapses into A->B.
"""

import logging
import math
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

ID_LOST_TYPE = "OTEIdLost"


def _to_utc(ts_ms) -> datetime:
    return datetime.fromtimestamp(int(ts_ms) / 1000.0, tz=timezone.utc)


def _xy(event: dict):
    """(x, y) in local metres, or None if the event carries no position (OTEIdLost).

    Z is dropped on purpose: the vendor says it is not a height measurement and may be
    pinned at 0, and reading it would turn a raised arm into movement. The push sends a
    bare {x, y, z} - in every located event of a sample push - so there is no other
    shape to normalise.
    """
    location = event.get("currentLocation") or {}
    x, y = location.get("x"), location.get("y")
    if x is None or y is None:
        return None
    return float(x), float(y)


def _distance(a, b) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1]) if a and b else 0.0


def _percentile(values: list, fraction: float) -> float:
    """Linear interpolation, numpy's default convention. Empty -> 0.0, never a hole."""
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    position = fraction * (len(ordered) - 1)
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return float(ordered[low])
    return float(ordered[low] + (ordered[high] - ordered[low]) * (position - low))


def _mean(values: list) -> float:
    return float(sum(values) / len(values)) if values else 0.0


# --- 1. Presence segments -------------------------------------------------------

def presence_segments(events, gap_seconds: float, window_end: datetime = None) -> list:
    """Stream of (device_id, event) -> one row per (objectId, device_id, segment).

    Never sorted: the dump is chronological per device and sorting would hold the window
    in memory. `window_end` separates "closed by silence" from "alive at the border".
    """
    open_segments = {}
    closed = []
    backwards = 0

    for device_id, event in events:
        object_id = event.get("objectId")
        timestamp = event.get("timeStamp")
        if not object_id or timestamp is None:
            continue
        seen_at = _to_utc(timestamp)
        key = (device_id, object_id)
        current = open_segments.get(key)

        if event.get("type") == ID_LOST_TYPE:
            # Does not always arrive - hence the gap below as a backstop.
            if current is not None:
                closed.append(_close(open_segments.pop(key), "id_lost"))
            continue

        if current is not None:
            # The distance to the segment, which is 0 while the event falls INSIDE it. By
            # distance and not by `seen_at - last_seen`: two archived objects overlap as
            # soon as a dump lands mid-run, so the stream is not strictly chronological,
            # and a plain subtraction went negative - past the gap check and into
            # last_seen, publishing negative stays and a negative aforo in green.
            distance = max((seen_at - current["last_seen"]).total_seconds(),
                           (current["first_seen"] - seen_at).total_seconds(), 0.0)
            if seen_at < current["last_seen"]:
                backwards += 1
            if distance > gap_seconds:
                closed.append(_close(open_segments.pop(key), "gap"))
                current = None

        position = _xy(event)
        if current is None:
            current = {
                "object_id": object_id, "device_id": device_id,
                "first_seen": seen_at, "last_seen": seen_at, "n_frames": 0,
                "first_position": position, "last_position": position,
                "path_length_m": 0.0, "labels_seen": set(),
            }
            open_segments[key] = current

        if position is not None:
            current["path_length_m"] += _distance(current["last_position"], position)
            if current["first_position"] is None:
                current["first_position"] = position
            current["last_position"] = position
        # min/max and not a plain assignment, for the same reason as the distance above.
        current["first_seen"] = min(current["first_seen"], seen_at)
        current["last_seen"] = max(current["last_seen"], seen_at)
        current["n_frames"] += 1
        seen_label = (event.get("labels") or {}).get("type")
        if seen_label:
            current["labels_seen"].add(seen_label)

    if backwards:
        logger.warning(f"{backwards} event(s) arrived out of order: two archived objects of "
                       "one device overlap in time. The metrics hold, the positions of "
                       "those tracks are read in the wrong order.")

    for segment in open_segments.values():
        still_alive = (window_end is None
                       or (window_end - segment["last_seen"]).total_seconds() <= gap_seconds)
        closed.append(_close(segment, "open" if still_alive else "gap"))

    return sorted(closed, key=lambda s: (s["first_seen"], s["object_id"], s["device_id"]))


def _close(segment: dict, reason: str) -> dict:
    """Fills in what is only known once the segment ends."""
    duration = (segment["last_seen"] - segment["first_seen"]).total_seconds()
    segment["duration_s"] = duration
    segment["displacement_m"] = _distance(segment["first_position"], segment["last_position"])
    segment["speed_avg_mps"] = segment["path_length_m"] / duration if duration > 0 else 0.0
    segment["closed_reason"] = reason
    return segment


# --- 2. Tracks ------------------------------------------------------------------

def resolve_label(labels_seen: set, priority: tuple = ()) -> str | None:
    """One final label for a track that may have been reported as more than one class
    inside a single report window - by PRIORITY, never by which was seen first or most.

    A raw value outside `priority` (an unexpected labels.type) is still returned - the
    lowest sorted, so the result is deterministic - instead of disappearing, so
    _warn_unpublished_labels can still flag it. Empty input is None, never a KeyError.
    """
    for label in priority:
        if label in labels_seen:
            return label
    leftover = labels_seen - set(priority)
    return min(leftover, default=None)


def tracks(segments: list, label_priority: tuple = ()) -> list:
    """Segments -> one row per objectId. Two LIDARs of the same space report the same id
    (the vendor merges identities), so one id in two devices IS the transit between them."""
    by_object = {}
    for segment in segments:
        by_object.setdefault(segment["object_id"], []).append(segment)

    result = []
    for object_id, own in by_object.items():
        ordered = sorted(own, key=lambda s: (s["first_seen"], s["device_id"]))
        last = max(own, key=lambda s: (s["last_seen"], s["first_seen"]))
        # Union over every segment of the track, not just the first that has one: the
        # priority resolution below needs everything ever seen, regardless of which
        # segment or device it came from.
        labels_seen = set().union(*(s["labels_seen"] for s in own))
        t_start = ordered[0]["first_seen"]
        t_end = last["last_seen"]
        # SPAN vs PRESENCE. The span holds the silences; the presence is the union of the
        # segments, so an id lost for 50 min and seen again is 20 s of stay, not 50 min.
        # Union and not a plain sum because two sensors of one zone overlap in time.
        presence = sum((end - start).total_seconds() for start, end
                       in _merge([(s["first_seen"], s["last_seen"]) for s in own]))
        path_length = sum(s["path_length_m"] for s in own)
        result.append({
            "object_id": object_id,
            "t_start": t_start,
            "t_end": t_end,
            "duration_s": (t_end - t_start).total_seconds(),
            "presence_s": presence,
            "device_ids": [(s["device_id"], s["first_seen"], s["last_seen"]) for s in ordered],
            "label": resolve_label(labels_seen, label_priority),
            # SUM: coordinates are local to each sensor, so there is no cross-device net.
            "displacement_m": sum(s["displacement_m"] for s in own),
            "path_length_m": path_length,
            # Over the PRESENCE: dividing by the span would count the silences as standing still.
            "speed_avg_mps": path_length / presence if presence > 0 else 0.0,
            "n_frames": sum(s["n_frames"] for s in own),
            # By the LAST segment: an id lost and seen again is not closed.
            "closed": last["closed_reason"] != "open",
        })
    return sorted(result, key=lambda t: (t["t_start"], t["object_id"]))


# --- 5. Transits ----------------------------------------------------------------

def transitions(track_rows: list) -> dict:
    """sensor -> sensor -> count, from consecutive pairs of each track's `device_ids`.

    One JSON object: an attribute per pair would be hundreds with a few dozen sensors.
    """
    pairs = {}
    for track in track_rows:
        # No filter needed: the caller passes tracks rebuilt from the zone's own
        # segments, so device_ids already holds only that zone's sensors.
        visited = [device_id for device_id, _first, _last in track["device_ids"]]
        for origin, destination in zip(visited, visited[1:]):
            if origin == destination:
                continue
            pairs.setdefault(origin, {})
            pairs[origin][destination] = pairs[origin].get(destination, 0) + 1
    return pairs


# --- 3. Zone metrics ------------------------------------------------------------

def zone_metrics(track_rows: list, segments: list, window: tuple, zone_of_device,
                 published_labels: list, stationary_max_m: float,
                 zone_ids: list = None, label_priority: tuple = ()) -> dict:
    """zone_id -> the attributes of §3, deduplicating objectId: someone seen by two
    LIDARs of the same zone is ONE person. `zone_ids` forces which zones are emitted.
    """
    segments_by_zone = {}
    unknown_devices = set()
    for segment in segments:
        zone_id = zone_of_device(segment["device_id"])
        if zone_id is None:
            unknown_devices.add(segment["device_id"])
            continue
        segments_by_zone.setdefault(zone_id, []).append(segment)
    if unknown_devices:
        logger.warning(f"Devices with no zone in zones_config, left out of the zone "
                       f"aggregate: {sorted(unknown_devices)}")

    _warn_unpublished_labels(track_rows, published_labels)

    zones = zone_ids if zone_ids is not None else sorted(segments_by_zone)

    metrics = {}
    for zone_id in zones:
        zone_segments = segments_by_zone.get(zone_id, [])
        # Rebuilt from the zone's OWN segments instead of picking the global track by id.
        # The global one aggregates every zone the objectId was seen in, so a person
        # crossing Z01 and Z03 published each zone's stay, path and displacement in BOTH.
        # Rebuilding also restricts device_ids to this zone, so transits need no filter.
        zone_tracks = tracks(zone_segments, label_priority)

        attributes = _metric_block(zone_tracks, zone_segments, window, "total",
                                   stationary_max_m)
        attributes["transitions"] = transitions(zone_tracks)

        # All configured labels, zero included: a sometimes-missing series is a
        # different feature to the model than one worth zero.
        for label in published_labels:
            labelled = [track for track in zone_tracks if track["label"] == label]
            wanted = {track["object_id"] for track in labelled}
            label_segments = [segment for segment in zone_segments
                              if segment["object_id"] in wanted]
            attributes.update(_metric_block(labelled, label_segments, window, label,
                                            stationary_max_m))
        metrics[zone_id] = attributes
    return metrics


def observed_metrics(track_rows: list, segments: list, window: tuple,
                     published_labels: list, stationary_max_m: float,
                     device_ids: list, label_priority: tuple = ()) -> dict:
    """device_id -> the same block as a zone, grouped by SENSOR instead of by zone.

    Nothing new is computed: `zone_of_device` is the identity, so zone_metrics() does the
    work. It exists because the sensors of a zone sit far enough apart, so the zone
    aggregate hides which of its six carries the traffic - and you can always add sensors
    up into a zone, never split a zone back into sensors.

    Every transit attribute is dropped: a sensor cannot transit to itself, so the matrix
    is always empty and the counts always zero. Three constant zeros per sensor is noise
    the importation job would happily turn into three attributes nobody reads.
    """
    metrics = zone_metrics(track_rows, segments, window, lambda device_id: device_id,
                           published_labels, stationary_max_m, zone_ids=device_ids,
                           label_priority=label_priority)
    for attributes in metrics.values():
        for key in [k for k in attributes if k == "transitions" or k.endswith("Transitions")]:
            del attributes[key]
    return metrics


def _warn_unpublished_labels(track_rows: list, published_labels: list):
    """A label outside the configured list counts in total* and gets no attribute."""
    seen = {track["label"] for track in track_rows if track["label"]}
    unpublished = sorted(seen - set(published_labels))
    if unpublished:
        logger.warning(f"labels.type not in OTE_LABEL_ATTRS, counted only in total*: "
                       f"{unpublished}")


def _metric_block(track_rows: list, segments: list, window: tuple, prefix: str,
                  stationary_max_m: float) -> dict:
    window_start, window_end = window
    concurrent_max, concurrent_avg = _concurrency(segments, window)
    # Only CLOSED tracks: a live one is truncated by the border and underestimates.
    stays = [track["presence_s"] for track in track_rows if track["closed"]]
    speeds = [track["speed_avg_mps"] for track in track_rows]

    return {
        f"{prefix}Count": len(track_rows),
        f"{prefix}ConcurrentMax": concurrent_max,
        f"{prefix}ConcurrentAvg": round(concurrent_avg, 3),
        # Approximated at the borders: only the window is read.
        f"{prefix}Entered": sum(1 for track in track_rows if track["t_start"] > window_start),
        f"{prefix}Exited": sum(1 for track in track_rows
                               if track["closed"] and track["t_end"] < window_end),
        f"{prefix}StayAvg": round(_mean(stays), 2),
        f"{prefix}StayP50": round(_percentile(stays, 0.50), 2),
        f"{prefix}StayP90": round(_percentile(stays, 0.90), 2),
        f"{prefix}StayMax": round(max(stays), 2) if stays else 0.0,
        f"{prefix}SpeedAvg": round(_mean(speeds), 3),
        f"{prefix}SpeedP90": round(_percentile(speeds, 0.90), 3),
        f"{prefix}PathLengthAvg": round(_mean([t["path_length_m"] for t in track_rows]), 2),
        f"{prefix}DisplacementAvg": round(_mean([t["displacement_m"] for t in track_rows]), 2),
        # COUNTS, does not filter: the threshold is decided later, without reprocessing.
        f"{prefix}StationaryCount": sum(1 for track in track_rows
                                        if track["displacement_m"] < stationary_max_m),
        f"{prefix}Transitions": sum(count
                                    for destinations in transitions(track_rows).values()
                                    for count in destinations.values()),
    }


def _concurrency(segments: list, window: tuple) -> tuple:
    """(max, time-weighted mean) of SIMULTANEOUS objects - the aforo, not the count:
    300 people can cross a square with never 12 at a time.
    """
    window_start, window_end = window
    intervals = []
    by_object = {}
    for segment in segments:
        by_object.setdefault(segment["object_id"], []).append(
            (segment["first_seen"], segment["last_seen"]))
    for own in by_object.values():
        intervals.extend(_merge(own))

    if not intervals:
        return 0, 0.0

    # +1 before -1 at the same instant, so a zero-length segment still counts as present.
    boundaries = sorted([(start, 1) for start, _end in intervals]
                        + [(end, -1) for _start, end in intervals],
                        key=lambda item: (item[0], -item[1]))

    running = 0
    peak = 0
    area = 0.0
    previous = boundaries[0][0]
    for instant, delta in boundaries:
        area += running * (instant - previous).total_seconds()
        previous = instant
        running += delta
        peak = max(peak, running)

    span = (window_end - window_start).total_seconds()
    return peak, (area / span if span > 0 else 0.0)


def _merge(intervals: list) -> list:
    """Union of one object's intervals, so overlapping sensors do not double count it."""
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


# --- 4. Device metrics ----------------------------------------------------------

def new_census() -> dict:
    """The frame census of one device, folded. Two counters and the RUNS of frames, not one
    row per frame: a few dozen sensors at 10 fps for an hour is 1.3 M rows and ~145 MB."""
    return {"frames": 0, "empty": 0, "runs": []}


def census_frame(census: dict, frame_at: datetime, event_count: int) -> None:
    """Folds one frame in.

    Frames are chronological WITHIN an archived object but not across two that overlap, so
    a frame going backwards opens a new run instead of being measured against the previous
    one. Subtracting against the latest instant made the gap negative and dropped it, and
    the hole the second object fills was published as silence: 15 minutes of invented
    silence on the very entity that exists to say whether the sensor was alive.
    Bounded by the number of jumps backwards - one per file boundary - not by the frames.
    """
    runs = census["runs"]
    if runs and frame_at >= runs[-1][1]:
        runs[-1][1] = frame_at
    else:
        runs.append([frame_at, frame_at])
    census["frames"] += 1
    if event_count == 0:
        census["empty"] += 1


def device_metrics(census_by_device: dict, window: tuple) -> dict:
    """device_id -> the device health of §4. Rates, not counts: a count stops being
    comparable if the window duration changes.
    """
    window_start, window_end = window
    span = (window_end - window_start).total_seconds()

    metrics = {}
    for device_id, census in census_by_device.items():
        frames = census["frames"]
        # United, so the runs of two overlapping objects do not read as a hole between them.
        covered = _merge([(start, end) for start, end in census["runs"]])
        last = covered[-1][1] if covered else None
        silence = (span if not covered else max(
            [(covered[0][0] - window_start).total_seconds(),
             (window_end - last).total_seconds()]
            + [(later[0] - earlier[1]).total_seconds()
               for earlier, later in zip(covered, covered[1:])]))
        metrics[device_id] = {
            "frameRate": round(frames / span, 3) if span > 0 else 0.0,
            "emptyFrameRatio": round(census["empty"] / frames, 3) if frames else 1.0,
            "silenceMaxSeconds": round(silence, 1),
            "lastFrameAt": last.isoformat().replace("+00:00", "Z") if last else None,
        }
    return metrics
