"""
Publishes FICTITIOUS measures into an the platform environment (production or local -
the environment variables decide, never the code), to validate the pipeline or to
fill an environment with plausible history by hand.

Two sources, a single script (--source):
    lidar       the three entities the ingestion ETL publishes per window
                (CrowdFlowLidarZone / ...Observed / ...Device), produced by running
                synthetic push frames through the ETL's OWN functions, so the fake data
                cannot drift from the real data.
    smartspot   aggregated Smart Spot counts (CrowdFlowObserved), via
                smartspot_transform.transform_smartspot_observed.

Two generation modes (--mode):
    fixture     DEFAULT. One hand-written case per source, with stable ids so re-running
                does not pile up entities: for lidar, one window of two sensors; for
                smartspot, one message per case (a zone at zero, ...). All at "now".
    random      A TIME SERIES generated around a mean: --entities entities x one
                point every --interval between --from and --to, each value
                randomized +-`--deviation` around --mean. For filling an
                environment with plausible history (train.py needs weeks of it),
                not for validating edge cases.

                --from/--to accept ANY instant, past or FUTURE: nothing is clamped
                to "now" (useful for pre-loading a demo or a dashboard with data
                ahead of the clock). Two things to keep in mind when dating
                forward: those points go into the SAME entity as the real history,
                so train.py reads them as if they were real measures; and
                predictions are not affected by them, because
                etl/predict/transform._default_start_ts caps the start of the
                horizon at min(last data point, now).

From Smart Spot only CrowdFlowObserved (aggregated crowd count) is posted - NEVER
CrowdFlowEvent, which carries MAC/visitorId.

Two publication routes (--route):
    iota    DEFAULT for --mode fixture. One POST per measure to the IoT Agent
            JSON, following the pattern documented by the team (IoT Agent
            endpoint, apikey as a query param, flat JSON body with TimeInstant).
            Fine for a handful of messages; it is documented as LOSING DATA UNDER
            LOAD, so it is not the route for a long series.
    batch   DEFAULT for --mode random. The reliable route, the same one the
            product itself uses: a WIDE CSV (urn,type,timestamp,<measures>) ->
            storage -> `platform.data.importation_job` on the queue, via
            helpers/uploader.py. The CSV is split into chunks of --batch-size
            rows (1000 by default) and one job is published per chunk.

            Why a single CSV can carry everything (verified in
            queues-consumer, not assumed): DataFrameParser groups the rows by
            (urn, tenant, scope, type) and emits ONE notification per entity with
            every attribute and its per-row timestamp, so N entities x M
            timestamps fit in one file. `urn`/`type` are read PER ROW from the CSV
            (DataImportationRequest only declares user_id/tenant/scope/
            storage_file_path, so the urn/type that uploader.py puts in the queue
            message are ignored by the job) - which is exactly why a multi-entity
            file works. Mandatory columns: `timestamp` (epoch or ISO 8601), `urn`
            (valid NGSI-LD) and `type`; empty cells are skipped, not written as
            nulls.

Configuration (via the environment or in .env - see .env.example):
    --route iota:
        IOTA_URL                IoT Agent JSON endpoint. No default on purpose:
                                the code must not know which environment it points to.
        IOTA_LIDAR_APIKEY       apikey of the LIDAR service group (--source lidar).
        IOTA_SMARTSPOT_APIKEY   apikey of the CrowdFlowObserved service group
                                (--source smartspot). They are different service
                                groups, hence the two variables.
    --route batch:
        QUEUES_CONSUMER_API_URL queues-consumer endpoint (/publish).
        STORAGE_TYPE + AWS_S3_* / LOCAL_*   where the CSV is uploaded.
        FIWARE_TENANT / FIWARE_SCOPE        destination of the data (--tenant/--scope
                                            override them for a one-off run).
    both:
        TEST_ENTITY_PREFIX      prefix of the LIDAR test IDs (default
                                "crowd_test_obj_").
        TEST_SMARTSPOT_PREFIX   prefix of the Smart Spot test IDs (default
                                "crowd_smartspot_test_").

Usage:
    # the 3 fixtures of each source, one POST each (what this script did before)
    python3 post_measures.py --source lidar --dry-run       # only builds and shows the payloads
    python3 post_measures.py --source lidar                 # really posts
    python3 post_measures.py --source smartspot

    # a random series: 6 sensors, one measure every 15 min for a whole month,
    # around 120 people +-15%, in batches of 1000 rows
    python3 post_measures.py --source smartspot --mode random \\
        --entities 6 --mean 120 --deviation 0.15 \\
        --from 2026-05-01T00:00:00Z --to 2026-05-31T23:45:00Z --interval 15m

    # the same thing but seeing the CSVs without publishing anything
    python3 post_measures.py --source smartspot --mode random --mean 120 \\
        --from 2026-05-01 --interval 1h --dry-run

--source has no default on purpose: whoever runs it has to say explicitly what
they are posting.

STABLE test IDs (<prefix>1..N) so as not to generate new entities on every run -
re-running updates the same test entities, it does not pollute the environment
with rubbish piling up. NOTE: changing the prefix creates NEW entities instead of
updating the previous ones. The Smart Spot IDs are also deliberately different
from the real SS1-SS4 ids of the installed sensors, so as not to mix test data
with real data.

"""

import argparse
import csv
import json
import os
import random
import re
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

from crowd_predictions.helpers.uploader import CSV_MANDATORY_COLUMNS
from crowd_predictions.smartspot_transform import transform_smartspot_observed

load_dotenv()

DEFAULT_TEST_ENTITY_PREFIX = "crowd_test_obj_"
DEFAULT_TEST_SMARTSPOT_PREFIX = "crowd_smartspot_test_"

# --mode random defaults
DEFAULT_ENTITIES = 3
DEFAULT_DEVIATION = 0.15   # +-15%, the same default as smart-city-data-generator
DEFAULT_INTERVAL = "1h"
DEFAULT_SEED = 42          # reproducible on purpose: two runs generate the same series

# --route batch defaults. 1000 rows/CSV is a middle ground: the job parses the whole
# file in memory and processes it entity by entity, so a single 500k-row CSV is one
# all-or-nothing job, and one row per file is one queue message per measure.
DEFAULT_BATCH_SIZE = 1000

# Backstop against "--from 2020 --interval 1s" - millions of measures that nobody
# wants and that would hammer the environment. Raise it with --max-messages if the
# volume really is intended.
DEFAULT_MAX_MESSAGES = 50_000
# How long a synthetic person stays in front of a sensor. From the real reading of
# Observed shape: the median stay per hour is tens of seconds, with a long tail.
STAY_SECONDS = (20.0, 120.0)

_INTERVAL_RE = re.compile(r"^\s*(\d+)\s*([smh]?)\s*$", re.IGNORECASE)
_INTERVAL_UNITS = {"s": 1, "m": 60, "h": 3600, "": 1}


def _iso_from_ms(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_interval(text: str) -> timedelta:
    """'30s' / '15m' / '1h' -> timedelta. A bare number is read as seconds."""
    match = _INTERVAL_RE.match(str(text))
    if not match:
        raise ValueError(f"Invalid interval: '{text}'. Expected something like 30s, 15m or 1h.")
    amount, unit = int(match.group(1)), match.group(2).lower()
    seconds = amount * _INTERVAL_UNITS[unit]
    if seconds <= 0:
        raise ValueError(f"The interval has to be greater than 0: '{text}'")
    return timedelta(seconds=seconds)


def parse_when(text: str) -> datetime:
    """ISO 8601 -> aware datetime in UTC. Accepts the 'Z' suffix and a bare date.

    A value with no timezone is interpreted as UTC (not as local time): the whole
    pipeline works in UTC and guessing the machine's zone here would silently shift
    the series.
    """
    raw = str(text).strip().replace("Z", "+00:00")
    try:
        when = datetime.fromisoformat(raw)
    except ValueError:
        raise ValueError(f"Invalid date: '{text}'. Expected ISO 8601, e.g. 2026-05-01T00:00:00Z.")
    return when.replace(tzinfo=timezone.utc) if when.tzinfo is None else when.astimezone(timezone.utc)


def align_down(when: datetime, step: timedelta) -> datetime:
    """Truncates `when` to the granularity of `step` (an hourly series lands on :00)."""
    when = when.replace(microsecond=0)
    if step >= timedelta(minutes=1):
        when = when.replace(second=0)
    if step >= timedelta(hours=1):
        when = when.replace(minute=0)
    return when


def count_timestamps(start: datetime, end: datetime, step: timedelta) -> int:
    """How many instants `build_timestamps` would return, without building them.

    Arithmetic on purpose: it is what lets the --max-messages guard run before the
    list exists (see build_messages)."""
    if end < start:
        raise ValueError("--to cannot be earlier than --from")
    return (end - start) // step + 1


def build_timestamps(start: datetime, end: datetime, step: timedelta) -> list:
    """List of instants in ms from `start` to `end` inclusive, one every `step`."""
    if end < start:
        raise ValueError("--to cannot be earlier than --from")
    stamps, cur = [], start
    while cur <= end:
        stamps.append(int(cur.timestamp() * 1000))
        cur += step
    return stamps


def randomize_value(mean: float, deviation: float, rng: random.Random,
                    integer: bool = True) -> float:
    """Uniform noise +-deviation around `mean`, never negative.

    Same approach as smart-city-data-generator (generate_city_sensors.randomize_value
    / baseline_patterns.apply_noise): uniform(mean*(1-deviation), mean*(1+deviation)).
    A uniform, not a gaussian, on purpose - it is what that generator does and it
    bounds the value inside the range instead of letting occasional outliers through.

    Difference from the original: with mean 0 it returns 0 flat (the generator gives
    a 5% chance of a 1). Here mean 0 means "a sensor at zero" and we want it to stay
    at zero, so the case can be validated.
    """
    if mean <= 0:
        return 0 if integer else 0.0
    value = rng.uniform(mean * (1 - deviation), mean * (1 + deviation))
    return max(0, int(round(value))) if integer else max(0.0, round(value, 2))


def _entity_id_from_urn(urn: str) -> str:
    return urn.rsplit(":", 1)[-1]


# Same sanitisation as etl/ote/load.py: the two build the same URNs, and a test prefix
# comes from the environment, so it can carry anything.
_URN_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _urn_safe(value: str) -> str:
    return _URN_UNSAFE.sub("_", str(value)).strip("_") or "unknown"


def _lidar_window_entities(window_start_ms: int, window_seconds: int, sensors: list,
                           mean: float, deviation: float, rng: random.Random,
                           prefix: str) -> list:
    """Synthetic push frames -> the entities the INGESTION ETL publishes for that window.

    Goes through the ETL's own pure functions (presence_segments / tracks /
    observed_metrics / zone_metrics / device_metrics) instead of re-deriving the
    attributes here. Writing them twice means the fake data drifts from the real data the
    first time either side changes, and there are 46 of them.

    `mean` is the average number of SIMULTANEOUS people per sensor - the crowd signal of a
    LIDAR is how many tracks are alive, not the value of any single one.
    """
    from crowd_predictions.config import settings
    from crowd_predictions.etl.ote.transform import (census_frame, device_metrics,
                                                      new_census, observed_metrics,
                                                      presence_segments, tracks,
                                                      zone_metrics)

    ote = settings.ote()
    window_start = datetime.fromtimestamp(window_start_ms / 1000, tz=timezone.utc)
    window = (window_start, window_start + timedelta(seconds=window_seconds))
    # 1 frame/s and not the sensor's 10: the aggregates are the same shape and it is 10x
    # less synthetic work. The real rate is what CrowdFlowLidarDevice.frameRate reports.
    step_ms = 1000
    labels = ote.label_attrs()

    stream, census_by_device = [], {}
    for sensor in sensors:
        census = census_by_device.setdefault(sensor, new_census())
        # Each person LIVES a while instead of being replaced whenever the population
        # fluctuates: churning ids on every tick made an hour with an aforo of 3 report
        # thousands of distinct people. Measured on a real hour: 104 people, aforo 4.
        alive = {}
        for at_ms in range(window_start_ms, window_start_ms + window_seconds * 1000, step_ms):
            for object_id in [i for i, (_x, _y, dies) in alive.items() if dies <= at_ms]:
                del alive[object_id]
            wanted = max(0, randomize_value(mean, deviation, rng))
            while len(alive) < wanted:
                # The sensor goes in the id so two of them cannot collide by creating
                # someone in the same millisecond: that produced people "transiting"
                # between sensors nine times, and sensors that far apart do not share
                # nobody. To exercise a transit, give two sensors the same id on purpose.
                born = f"TrackingAggregator:{sensor}-{at_ms:x}{len(alive)}"
                alive[born] = (rng.uniform(-15, 15), rng.uniform(-15, 15),
                               at_ms + int(rng.uniform(*STAY_SECONDS) * 1000))
            for object_id, (x, y, dies) in list(alive.items()):
                stream.append((sensor, {
                    "type": "OTETrajectoryUpdate", "timeStamp": at_ms, "objectId": object_id,
                    "currentLocation": {"x": round(x, 2), "y": round(y, 2), "z": 0.9},
                    "absorbedObjectIds": [],
                    "labels": {"type": labels[0]} if labels else {},
                }))
                alive[object_id] = (x + rng.uniform(-1, 1), y + rng.uniform(-1, 1), dies)
            census_frame(census, datetime.fromtimestamp(at_ms / 1000, tz=timezone.utc),
                         len(alive))

    segments = presence_segments(iter(stream), ote.OTE_TRACK_GAP_SECONDS,
                                 window_end=window[1])
    track_rows = tracks(segments)
    # One synthetic zone for every synthetic sensor: they are not in zones_config, and
    # putting them there would leak test ids into the real map.
    zone_id = f"{prefix}zone"
    messages = []
    for entity_type, metrics in (
            (ote.OTE_ZONE_ENTITY_TYPE,
             zone_metrics(track_rows, segments, window, lambda _device: zone_id, labels,
                          ote.OTE_STATIONARY_MAX_DISPLACEMENT_M, zone_ids=[zone_id])),
            (ote.OTE_OBSERVED_ENTITY_TYPE,
             observed_metrics(track_rows, segments, window, labels,
                              ote.OTE_STATIONARY_MAX_DISPLACEMENT_M, sensors)),
            (ote.OTE_DEVICE_ENTITY_TYPE, device_metrics(census_by_device, window))):
        for entity_id, attributes in sorted(metrics.items()):
            messages.append({
                "_entityType": entity_type,
                "_entityId": entity_id,
                "_timeStampMs": window_start_ms,
                # The window START, so re-running republishes the same sample: same rule as
                # etl/ote/load.py, which is the only reason this is idempotent.
                **{key: (json.dumps(value, sort_keys=True) if isinstance(value, dict) else value)
                   for key, value in attributes.items()},
            })
    return messages


def generate_fake_lidar_messages(base_ts_ms: int, prefix: str = DEFAULT_TEST_ENTITY_PREFIX) -> list:
    """One window of two fictitious sensors, with stable ids so re-running does not pile up
    new entities. Publishes the same three entity types the real ingestion does."""
    return _lidar_window_entities(base_ts_ms, 3600, [f"{prefix}1", f"{prefix}2"],
                                  mean=3, deviation=0.3, rng=random.Random(DEFAULT_SEED),
                                  prefix=prefix)


def transform_lidar(msg: dict, ingest_ts_ms: Optional[int] = None) -> Optional[dict]:
    """Message -> key-values entity. Almost the identity: the aggregation already happened
    in the generator, through the real ETL."""
    entity_type, entity_id = msg.get("_entityType"), msg.get("_entityId")
    if not entity_type or not entity_id:
        return None
    return {
        "id": f"urn:ngsi-ld:{entity_type}:{_urn_safe(entity_id)}",
        "type": entity_type,
        "_timeStampMs": msg["_timeStampMs"],
        **{key: value for key, value in msg.items() if not key.startswith("_")},
    }


def generate_fake_smartspot_messages(base_ts_ms: int,
                                      prefix: str = DEFAULT_TEST_SMARTSPOT_PREFIX) -> list:
    """
    Fictitious aggregated Smart Spot counts for a few test devices
    (<prefix>1..N). It covers: a quiet zone (low counts), a busy zone (high
    counts), and a long window larger than the short one (accumulated over the
    day vs at the moment), to validate that the IoT Agent accepts and exposes the
    3 windows separately.
    """
    return [
        {
            "device_id": f"{prefix}1",
            "timestamp_ms": base_ts_ms,
            "peopleCountShortInterval": 8,
            "peopleCountMediumInterval": 34,
            "peopleCountLongInterval": 210,
        },
        {
            "device_id": f"{prefix}2",
            "timestamp_ms": base_ts_ms,
            "peopleCountShortInterval": 42,
            "peopleCountMediumInterval": 260,
            "peopleCountLongInterval": 1830,
        },
        {
            "device_id": f"{prefix}3",
            "timestamp_ms": base_ts_ms,
            "peopleCountShortInterval": 0,
            "peopleCountMediumInterval": 0,
            "peopleCountLongInterval": 5,
        },
    ]


def generate_random_smartspot_messages(timestamps_ms: list, mean: float, deviation: float,
                                        entities: int, prefix: str,
                                        rng: random.Random) -> list:
    """Random Smart Spot series: `entities` devices x one count per instant.

    `mean` is the average of peopleCountMediumInterval - the measure the model
    consumes (CROWD_MEASURE_ID) - and the other two windows are derived from it
    instead of being randomized on their own: the three counts of a real sensor are
    the same people counted over 1/5/10 min, so drawing them independently would
    produce impossible combinations (a short window above the long one).

    The ratios come from smart-city-data-generator (crowd-flow/generate_crowdflow.py,
    where the long window is the base): medium ~= 0.45-0.55 * long and short ~=
    0.08-0.13 * long. Inverted, relative to medium: long ~= 1.8-2.2 * medium and
    short ~= 0.16-0.28 * medium.
    """
    messages = []
    for ts_ms in timestamps_ms:
        for n in range(1, entities + 1):
            medium = randomize_value(mean, deviation, rng)
            long_interval = max(medium, int(round(medium * rng.uniform(1.8, 2.2))))
            short_interval = int(round(medium * rng.uniform(0.16, 0.28)))
            messages.append({
                "device_id": f"{prefix}{n}",
                "timestamp_ms": ts_ms,
                "peopleCountShortInterval": short_interval,
                "peopleCountMediumInterval": medium,
                "peopleCountLongInterval": long_interval,
            })
    return messages


def generate_random_lidar_messages(timestamps_ms: list, mean: float, deviation: float,
                                   entities: int, prefix: str, rng: random.Random) -> list:
    """A series of WINDOWS: each instant is one aggregation window, `entities` sensors wide.

    `mean` is the average number of SIMULTANEOUS people per sensor, not the value of any
    one attribute: what a LIDAR measures is how many tracks are alive at once.

    The window length is taken from the gap between instants, so `--interval 1h` produces
    the hourly windows the real CronJob publishes.
    """
    sensors = [f"{prefix}{n}" for n in range(1, entities + 1)]
    span = ((timestamps_ms[1] - timestamps_ms[0]) // 1000 if len(timestamps_ms) > 1
            else 3600)
    return [message
            for ts_ms in timestamps_ms
            for message in _lidar_window_entities(ts_ms, span, sensors, mean, deviation,
                                                  rng, prefix)]


# Everything that differentiates the two sources, in a single place.
#
# Both sources now carry the instant in the same internal key, "_timeStampMs", which the
# transform adds and which must NOT reach the body (hence it is in drop_keys). It used to
# differ: the LIDAR path published OTEDetection, where `timeStamp` was a real property of
# the entity and also had to be dropped from the CSV, because the importation job matches
# columns case-insensitively and it collided with the mandatory `timestamp`.
SOURCES = {
    "lidar": {
        "label": "windows",
        "transform": transform_lidar,
        "generate": generate_fake_lidar_messages,
        "generate_random": generate_random_lidar_messages,
        "apikey_env": "IOTA_LIDAR_APIKEY",
        "prefix_env": "TEST_ENTITY_PREFIX",
        "default_prefix": DEFAULT_TEST_ENTITY_PREFIX,
        "ts_field": "_timeStampMs",
        "drop_keys": ("id", "type", "_timeStampMs"),
        "csv_drop_keys": (),
        "skip_reason": "no entity type or id",
    },
    "smartspot": {
        "label": "counts",
        "transform": transform_smartspot_observed,
        "generate": generate_fake_smartspot_messages,
        "generate_random": generate_random_smartspot_messages,
        "apikey_env": "IOTA_SMARTSPOT_APIKEY",
        "prefix_env": "TEST_SMARTSPOT_PREFIX",
        "default_prefix": DEFAULT_TEST_SMARTSPOT_PREFIX,
        "ts_field": "_timeStampMs",
        "site_field": None,
        "drop_keys": ("id", "type", "_timeStampMs"),
        "csv_drop_keys": (),  # no column of CrowdFlowObserved collides with `timestamp`
        "skip_reason": "no device_id",
    },
}


def build_body(entity: dict, source: str) -> dict:
    """Key-values entity -> flat IoT Agent body, with TimeInstant.

    The keys that are not measures are removed (id/type, plus the internal ones of
    the transform) and TimeInstant is derived from the timestamp field of that
    source (see the SOURCES comment: it is not the same field in the two).
    """
    cfg = SOURCES[source]
    body = {k: v for k, v in entity.items() if k not in cfg["drop_keys"]}
    body["TimeInstant"] = _iso_from_ms(entity[cfg["ts_field"]])
    return body


# Nested keys carrying {lat, lon}: in the CSV they travel as flat latitude/longitude,
# the same convention as etl/crowd/transform.py (the bulk import has no confirmed
# composite-column encoding for a GeoProperty).
_GEO_KEYS = ("location", "sensorLocation")

# Shared with the two ETLs so the three producers cannot drift.
CSV_LEADING_COLUMNS = CSV_MANDATORY_COLUMNS


def build_csv_row(entity: dict, source: str) -> dict:
    """Key-values entity -> flat row of the WIDE CSV that the importation job reads.

    Mandatory columns: urn (the entity id), type and timestamp; everything else is
    read as an attribute of the entity at that timestamp.
    """
    cfg = SOURCES[source]
    row = {
        "urn": entity["id"],
        "type": entity["type"],
        "timestamp": _iso_from_ms(entity[cfg["ts_field"]]),
    }
    for key, value in entity.items():
        if key in cfg["drop_keys"] or key in cfg["csv_drop_keys"] or value is None:
            continue
        if key in _GEO_KEYS:
            row["latitude"], row["longitude"] = value["lat"], value["lon"]
        elif isinstance(value, dict):
            # location3D: x/y/z already travel flat in currentLocation{X,Y,Z}, and a
            # nested dict in a CSV cell would arrive as an opaque Property.
            continue
        elif isinstance(value, (list, tuple)):
            # absorbedObjectIds: the parser (_parse_value) turns the JSON back into a list.
            row[key] = json.dumps(list(value))
        else:
            row[key] = value
    return row


def write_csv_chunk(rows: list, path: Path) -> Path:
    """Writes a chunk of rows as a WIDE CSV.

    The columns are the union of the keys of the chunk (not those of the first row):
    not every entity carries the same ones (an unknown device has no
    latitude/longitude, a track with no merge has no absorbedObjectIds). The gaps go
    out empty and the parser skips them instead of writing a null.
    """
    extra = sorted({k for row in rows for k in row} - set(CSV_LEADING_COLUMNS))
    fieldnames = list(CSV_LEADING_COLUMNS) + extra

    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, restval="")
        writer.writeheader()
        writer.writerows(rows)
    return path


def _chunks(items: list, size: int):
    for start in range(0, len(items), size):
        yield items[start:start + size]


def _transform(cfg: dict, msg: dict, ingest_ts_ms: int = None):
    """Calls cfg["transform"] with `site` only for sources that take one (see
    "site_field" in SOURCES) - transform_smartspot_observed() has no such argument."""
    kwargs = {"ingest_ts_ms": ingest_ts_ms}
    if cfg.get("site_field"):
        kwargs["site"] = msg.get(cfg["site_field"])
    return cfg["transform"](msg, **kwargs)


def post_batch(messages: list, source: str, batch_size: int = DEFAULT_BATCH_SIZE,
               ingest_ts_ms: int = None, tenant: str = None, scope: str = None,
               csv_dir: str = None, dry_run: bool = False) -> tuple:
    """Publishes the measures via CSV -> storage -> platform.data.importation_job.

    One CSV (and one queue job) per chunk of `batch_size` rows. Returns
    (published_jobs, total_jobs); in dry-run nothing is published and the CSVs are
    left on disk to be inspected.
    """
    cfg = SOURCES[source]

    rows = []
    for msg in messages:
        entity = _transform(cfg, msg, ingest_ts_ms=ingest_ts_ms)
        if entity is None:
            print(f"SKIP ({cfg['skip_reason']}): {msg}")
            continue
        rows.append(build_csv_row(entity, source))

    if not rows:
        print("Nothing to publish: every message was skipped.")
        return 0, 0

    output_dir = Path(csv_dir) if csv_dir else Path(tempfile.mkdtemp(prefix="post_measures_"))
    output_dir.mkdir(parents=True, exist_ok=True)

    chunks = list(_chunks(rows, batch_size))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    n_ok = 0

    # Imported here and not at the top: the iota route must not require the storage
    # configuration (helpers/uploader.py -> config.config.get_storage) just to run.
    if not dry_run:
        from crowd_predictions.helpers.uploader import upload_csv_via_s3_and_queue

    for index, chunk in enumerate(chunks, start=1):
        path = write_csv_chunk(chunk, output_dir / f"{source}_{stamp}_{index:04d}.csv")
        entities = sorted({row["urn"] for row in chunk})

        if dry_run:
            print(f"[DRY-RUN] batch {index}/{len(chunks)}: {len(chunk)} rows, "
                  f"{len(entities)} entities -> {path}")
            n_ok += 1
            continue

        # The urn is only used for the log and for the name in storage: the job reads
        # the urn/type of every row from the CSV (see the module docstring).
        ok = upload_csv_via_s3_and_queue(str(path), entities[0], tenant=tenant, scope=scope)
        print(("OK   " if ok else "ERROR"),
              f"batch {index}/{len(chunks)}: {len(chunk)} rows, {len(entities)} entities")
        n_ok += bool(ok)

    print(f"\nCSVs at {output_dir}")
    return n_ok, len(chunks)


def post_measure(msg: dict, apikey: str, source: str, iota_url: str = None,
                 ingest_ts_ms: int = None, dry_run: bool = False,
                 verbose: bool = True) -> bool:
    """Transforms a raw message and posts it to the IoT Agent (or shows it, in dry-run)."""
    cfg = SOURCES[source]
    entity = _transform(cfg, msg, ingest_ts_ms=ingest_ts_ms)
    if entity is None:
        print(f"SKIP ({cfg['skip_reason']}): {msg}")
        return False

    entity_id = _entity_id_from_urn(entity["id"])
    body = build_body(entity, source)

    if dry_run:
        print(f"[DRY-RUN] POST i={entity_id}")
        if verbose:
            print(json.dumps(body, indent=2, ensure_ascii=False))
        return True

    resp = requests.post(
        iota_url,
        params={"i": entity_id, "k": apikey},
        json=body,
        headers={"Content-Type": "application/json"},
        timeout=15,
    )
    # NOTE: the IoT Agent can return 200/201/204 and STILL carry an error in the
    # body (e.g. "ENTITY_GENERIC_ERROR") - the HTTP code alone is not enough, the
    # content of the response has to be looked at too.
    body_has_error = "error" in resp.text.lower()
    ok = resp.status_code in (200, 201, 204) and not body_has_error
    # With a long series (--mode random) one line per measure buries the failures:
    # when not verbose only what went wrong is printed.
    if verbose or not ok:
        print(("OK   " if ok else "ERROR"), entity_id, resp.status_code)
    if not ok:
        print(f"  Full response: {resp.text}")
    return ok


def build_messages(args, cfg: dict, prefix: str, base_ts_ms: int) -> list:
    """Messages to publish, according to --mode. Exits with 1 if the volume is unreasonable."""
    if args.mode == "fixture":
        return cfg["generate"](base_ts_ms, prefix=prefix)

    step = parse_interval(args.interval)
    end = align_down(parse_when(args.to) if args.to else datetime.now(timezone.utc), step)
    start = align_down(parse_when(getattr(args, "from")), step) if getattr(args, "from") else end
    # Counted before the list exists: with a 1 s interval over months it is
    # materializing the instants that eats the machine, so a guard that builds them
    # first would arrive too late to prevent anything.
    try:
        instants = count_timestamps(start, end, step)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    estimated = instants * args.entities
    if estimated > args.max_messages:
        print(f"ERROR: {estimated:,} measures ({instants:,} instants x {args.entities} "
              f"entities) exceeds --max-messages ({args.max_messages:,}).")
        print("       Narrow --from/--to, widen --interval, or raise --max-messages.")
        sys.exit(1)

    stamps = build_timestamps(start, end, step)
    print(f"Series: {start.isoformat()} -> {end.isoformat()} every {args.interval} "
          f"({len(stamps):,} instants) x {args.entities} entities, mean {args.mean} "
          f"+-{args.deviation:.0%}, seed {args.seed}")
    return cfg["generate_random"](stamps, args.mean, args.deviation, args.entities,
                                  prefix, random.Random(args.seed))


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", required=True, choices=sorted(SOURCES),
                        help="Which source of fictitious data to post (mandatory, no default)")
    parser.add_argument("--mode", choices=("fixture", "random"), default="fixture",
                        help="fixture: the hand-written messages (default). "
                             "random: a series around --mean")
    parser.add_argument("--route", choices=("iota", "batch"),
                        help="iota: one POST per measure to the IoT Agent. "
                             "batch: CSV -> storage -> importation job on the queue. "
                             "Default: iota with --mode fixture, batch with --mode random")
    parser.add_argument("--dry-run", action="store_true",
                        help="Builds and shows the payloads/CSVs without publishing anything")

    series = parser.add_argument_group("--mode random")
    series.add_argument("--mean", type=float, default=0.0,
                        help="Mean of the measure: peopleCountMediumInterval (smartspot) "
                             "or simultaneous detections (lidar)")
    series.add_argument("--deviation", type=float, default=DEFAULT_DEVIATION,
                        help=f"Fraction of variation around the mean, uniform "
                             f"(default {DEFAULT_DEVIATION} = +-15%%)")
    series.add_argument("--entities", type=int, default=DEFAULT_ENTITIES,
                        help=f"How many entities to generate, <prefix>1..N "
                             f"(default {DEFAULT_ENTITIES})")
    series.add_argument("--from", dest="from", metavar="ISO",
                        help="Start of the series, ISO 8601 (default: same as --to, one single point)")
    series.add_argument("--to", metavar="ISO",
                        help="End of the series, inclusive, ISO 8601 (default: now)")
    series.add_argument("--interval", default=DEFAULT_INTERVAL,
                        help=f"Time between measures: 30s, 15m, 1h (default {DEFAULT_INTERVAL})")
    series.add_argument("--seed", type=int, default=DEFAULT_SEED,
                        help=f"Seed of the generator, reproducible (default {DEFAULT_SEED})")
    series.add_argument("--max-messages", type=int, default=DEFAULT_MAX_MESSAGES,
                        help=f"Guard against absurd volumes (default {DEFAULT_MAX_MESSAGES:,})")

    batch = parser.add_argument_group("--route batch")
    batch.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                       help=f"Rows per CSV/job (default {DEFAULT_BATCH_SIZE})")
    batch.add_argument("--tenant", help="Destination tenant (default: FIWARE_TENANT)")
    batch.add_argument("--scope", help="Destination scope (default: FIWARE_SCOPE)")
    batch.add_argument("--csv-dir",
                       help="Where to leave the generated CSVs (default: a temporary directory)")

    args = parser.parse_args()

    if args.mode == "random" and args.mean <= 0:
        parser.error("--mode random needs a --mean greater than 0")
    if args.entities < 1:
        parser.error("--entities has to be at least 1")
    if not 0 <= args.deviation < 1:
        parser.error("--deviation is a fraction in [0, 1): 0.15 = +-15%")
    if args.batch_size < 1:
        parser.error("--batch-size has to be at least 1")
    if args.mode == "random":
        try:
            parse_interval(args.interval)
        except ValueError as exc:
            parser.error(str(exc))

    # The route is chosen by the mode when it is not given: a series of thousands of
    # measures over the IoT Agent (one POST each, and it loses data under load) is
    # never what you want.
    route = args.route or ("batch" if args.mode == "random" else "iota")

    cfg = SOURCES[args.source]
    apikey = os.environ.get(cfg["apikey_env"])
    iota_url = os.environ.get("IOTA_URL")
    prefix = os.environ.get(cfg["prefix_env"], cfg["default_prefix"])

    # In dry-run nothing is published, so no destination is needed. Each route needs
    # ITS OWN variables: the storage ones are validated inside helpers/uploader.py.
    if not args.dry_run:
        required = (("IOTA_URL", iota_url), (cfg["apikey_env"], apikey)) if route == "iota" else \
                   (("QUEUES_CONSUMER_API_URL", os.environ.get("QUEUES_CONSUMER_API_URL")),)
        missing = [name for name, value in required if not value]
        if missing:
            print(f"ERROR: missing from the environment: {', '.join(missing)}.")
            print("       Define it/them in .env (see .env.example) or export it/them:")
            if route == "iota":
                print('       export IOTA_URL="https://<iot-agent>/iot/json"')
                print(f'       export {cfg["apikey_env"]}="..."')
            else:
                print('       export QUEUES_CONSUMER_API_URL="https://<queues-consumer>"')
            sys.exit(1)

    base_ts_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    messages = build_messages(args, cfg, prefix, base_ts_ms)

    if route == "batch":
        target = "(dry-run, nothing is published)" if args.dry_run else \
                 f"{os.environ.get('QUEUES_CONSUMER_API_URL')} (tenant " \
                 f"{args.tenant or os.environ.get('FIWARE_TENANT')})"
        print(f"{'[DRY-RUN] ' if args.dry_run else ''}Publishing {len(messages):,} "
              f"{cfg['label']} from '{args.source}' (prefix '{prefix}') in batches of "
              f"{args.batch_size} rows -> {target}...")
        n_ok, total = post_batch(messages, args.source, batch_size=args.batch_size,
                                 ingest_ts_ms=base_ts_ms, tenant=args.tenant, scope=args.scope,
                                 csv_dir=args.csv_dir, dry_run=args.dry_run)
        print(f"Summary: {n_ok}/{total} batches OK ({len(messages):,} measures)")
        sys.exit(0 if total and n_ok == total else 1)

    target = "(dry-run, no destination)" if args.dry_run else iota_url
    print(f"{'[DRY-RUN] ' if args.dry_run else ''}Posting {len(messages)} test {cfg['label']} "
          f"from '{args.source}' (prefix '{prefix}') to {target}...")
    # With many measures the full payload of each one floods the terminal: only the
    # failures are printed (and a progress line every 100).
    verbose = len(messages) <= 50
    results = []
    for index, msg in enumerate(messages, start=1):
        results.append(post_measure(msg, apikey, args.source, iota_url=iota_url,
                                    ingest_ts_ms=base_ts_ms, dry_run=args.dry_run,
                                    verbose=verbose))
        if not verbose and index % 100 == 0:
            print(f"  ... {index}/{len(messages)} ({sum(results)} OK)")

    n_ok = sum(results)
    print(f"\nSummary: {n_ok}/{len(messages)} OK")

