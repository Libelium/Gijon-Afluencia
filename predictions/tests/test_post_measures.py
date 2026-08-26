"""Tests of the unified publication script (post_measures.py).

The important thing they cover:
  - the body construction is NOT the same for lidar and for smartspot (a different
    timestamp field and different internal keys to exclude), and a 200 with "error"
    in the body is NOT a success;
  - the CSV of --route batch does not collide with the mandatory `timestamp` column
    (the parser identifies columns case-insensitively, so OTEDetection.timeStamp
    would win over it and date everything in ms);
  - --mode random respects the mean/deviation, the interval and the number of
    entities, and it is reproducible with the same seed.
No network: requests.post is mocked.
"""

import contextlib
import csv
import io
import json
import os
import random
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, Mock

import pytest

import crowd_predictions.fake_measures as post_measures
from crowd_predictions.fake_measures import (
    build_body,
    build_csv_row,
    build_timestamps,
    count_timestamps,
    generate_fake_lidar_messages,
    generate_fake_smartspot_messages,
    generate_random_lidar_messages,
    generate_random_smartspot_messages,
    parse_interval,
    parse_when,
    post_batch,
    post_measure,
    randomize_value,
    write_csv_chunk,
    _iso_from_ms,
)

BASE_TS_MS = 1_760_000_000_000  # 2025-10-09T08:53:20Z

def _fake_response(status_code=200, text="{}"):
    resp = Mock()
    resp.status_code = status_code
    resp.text = text
    return resp


def test_smartspot_body_drops_internal_timestamp_and_uses_it_for_time_instant():
    """_timeStampMs is an internal key of the transform: it is used to derive
    TimeInstant and it must NOT reach the IoT Agent body."""
    msg = generate_fake_smartspot_messages(BASE_TS_MS)[0]
    entity = post_measures.transform_smartspot_observed(msg)
    body = build_body(entity, "smartspot")

    assert "_timeStampMs" in entity        # the transform does produce it
    assert "_timeStampMs" not in body      # but the body does not carry it
    assert "id" not in body and "type" not in body
    assert body["TimeInstant"] == _iso_from_ms(entity["_timeStampMs"])
    assert body["TimeInstant"] == "2025-10-09T08:53:20Z"


def test_lidar_time_instant_is_the_window_start():
    """The sample is dated with the START of the aggregation window, the same rule as
    etl/ote/load.py - which is the only reason re-publishing a window is idempotent."""
    msg = generate_fake_lidar_messages(BASE_TS_MS)[0]
    entity = post_measures.transform_lidar(msg)
    body = build_body(entity, "lidar")

    assert entity["_timeStampMs"] == BASE_TS_MS
    assert body["TimeInstant"] == "2025-10-09T08:53:20Z"
    assert "_timeStampMs" not in body                 # internal to the transform
    assert "id" not in body and "type" not in body


def test_both_sources_carry_the_instant_in_the_same_internal_key():
    """They used to differ, and that WAS the trap: the LIDAR path published OTEDetection,
    where `timeStamp` was a real property of the entity. Now both put the instant in
    `_timeStampMs`, which the transform adds and neither body may carry."""
    for source in ("lidar", "smartspot"):
        assert post_measures.SOURCES[source]["ts_field"] == "_timeStampMs"
        assert "_timeStampMs" in post_measures.SOURCES[source]["drop_keys"]


def test_generated_ids_respect_the_prefix():
    """The test IDs are stable on purpose; the prefix is parameterized so that the
    name does not carry the city inside it."""
    lidar = generate_fake_lidar_messages(BASE_TS_MS, prefix="otra_ciudad_obj_")
    assert all("otra_ciudad_obj_" in m["_entityId"] for m in lidar)

    smartspot = generate_fake_smartspot_messages(BASE_TS_MS, prefix="otra_ciudad_ss_")
    assert all(m["device_id"].startswith("otra_ciudad_ss_") for m in smartspot)


def test_default_prefixes_are_the_documented_ones():
    assert post_measures.DEFAULT_TEST_ENTITY_PREFIX == "crowd_test_obj_"
    assert post_measures.DEFAULT_TEST_SMARTSPOT_PREFIX == "crowd_smartspot_test_"
    lidar = generate_fake_lidar_messages(BASE_TS_MS)
    assert all("crowd_test_obj_" in m["_entityId"] for m in lidar)
    smartspot = generate_fake_smartspot_messages(BASE_TS_MS)
    assert all(m["device_id"].startswith("crowd_smartspot_test_") for m in smartspot)


def test_error_in_body_is_a_failure_even_with_status_200():
    """The IoT Agent can return 200/201/204 and still carry an error in the body
    (ENTITY_GENERIC_ERROR): the HTTP code alone is not enough."""
    msg = generate_fake_smartspot_messages(BASE_TS_MS)[0]
    resp = _fake_response(200, '{"name":"ENTITY_GENERIC_ERROR","message":"..."}')
    with patch("crowd_predictions.fake_measures.requests.post", return_value=resp) as mock_post:
        ok = post_measure(msg, "apikey", "smartspot", iota_url="http://iota/iot/json")
    assert mock_post.call_count == 1
    assert ok is False


def test_status_200_without_error_is_a_success():
    msg = generate_fake_smartspot_messages(BASE_TS_MS)[0]
    with patch("crowd_predictions.fake_measures.requests.post", return_value=_fake_response(200, "")) as mock_post:
        ok = post_measure(msg, "apikey", "smartspot", iota_url="http://iota/iot/json")
    assert ok is True
    kwargs = mock_post.call_args.kwargs
    assert kwargs["params"]["k"] == "apikey"
    assert "_timeStampMs" not in kwargs["json"]


def test_non_2xx_is_a_failure():
    msg = generate_fake_lidar_messages(BASE_TS_MS)[0]
    with patch("crowd_predictions.fake_measures.requests.post", return_value=_fake_response(500, "boom")):
        assert post_measure(msg, "apikey", "lidar", iota_url="http://iota/iot/json") is False


def test_dry_run_does_not_call_requests_post():
    with patch("crowd_predictions.fake_measures.requests.post") as mock_post:
        for source, messages in (("lidar", generate_fake_lidar_messages(BASE_TS_MS)),
                                 ("smartspot", generate_fake_smartspot_messages(BASE_TS_MS))):
            for msg in messages:
                assert post_measure(msg, None, source, dry_run=True) is True
    assert mock_post.call_count == 0


def test_unsupported_message_is_skipped_without_posting():
    with patch("crowd_predictions.fake_measures.requests.post") as mock_post:
        assert post_measure({"type": "OTEUnknown"}, "apikey", "lidar",
                            iota_url="http://iota/iot/json") is False
        assert post_measure({}, "apikey", "smartspot",
                            iota_url="http://iota/iot/json") is False
    assert mock_post.call_count == 0


def test_main_takes_the_prefix_from_the_environment_variable():
    """The prefix is read from the environment (TEST_ENTITY_PREFIX /
    TEST_SMARTSPOT_PREFIX); changing it creates NEW entities instead of updating
    the usual test ones."""
    cases = (("lidar", "TEST_ENTITY_PREFIX", "env_lidar_"),
             ("smartspot", "TEST_SMARTSPOT_PREFIX", "env_ss_"))
    for source, env_name, prefix in cases:
        with patch.dict(os.environ, {env_name: prefix}), \
                patch("crowd_predictions.fake_measures.requests.post") as mock_post, \
                patch("sys.argv", ["post_measures.py", "--source", source, "--dry-run"]), \
                patch("builtins.print") as mock_print:
            post_measures.main()
        output = " ".join(str(a) for call in mock_print.call_args_list for a in call.args)
        assert f"prefix '{prefix}'" in output
        assert prefix in output
        assert mock_post.call_count == 0


def test_main_exits_1_listing_the_missing_variables():
    """Without --dry-run and without the environment: a clear message with what is
    missing, and exit(1)."""
    with patch.dict(os.environ, {}, clear=True), \
            patch("crowd_predictions.fake_measures.requests.post") as mock_post, \
            patch("sys.argv", ["post_measures.py", "--source", "smartspot"]), \
            patch("builtins.print") as mock_print:
        try:
            post_measures.main()
            raise AssertionError("SystemExit was expected")
        except SystemExit as exc:
            assert exc.code == 1
    output = " ".join(str(a) for call in mock_print.call_args_list for a in call.args)
    assert "IOTA_URL" in output and "IOTA_SMARTSPOT_APIKEY" in output
    assert mock_post.call_count == 0


def test_source_is_required_and_validated():
    """No default on purpose: whoever runs it has to say what they are posting."""
    for argv in (["post_measures.py", "--dry-run"],
                 ["post_measures.py", "--source", "inventada", "--dry-run"]):
        stderr = io.StringIO()
        with patch("sys.argv", argv), contextlib.redirect_stderr(stderr):
            try:
                post_measures.main()
                raise AssertionError(f"SystemExit was expected for {argv}")
            except SystemExit as exc:
                assert exc.code == 2
        assert "--source" in stderr.getvalue()


def test_interval_accepts_seconds_minutes_hours_and_rejects_nonsense():
    assert parse_interval("30s") == timedelta(seconds=30)
    assert parse_interval("15m") == timedelta(minutes=15)
    assert parse_interval("1h") == timedelta(hours=1)
    assert parse_interval("90") == timedelta(seconds=90)   # bare number = seconds
    for bad in ("0s", "-5m", "1d", "un rato", ""):
        try:
            parse_interval(bad)
            raise AssertionError(f"ValueError was expected for {bad!r}")
        except ValueError:
            pass


def test_naive_dates_are_read_as_utc_not_as_local_time():
    """Guessing the machine's zone here would silently shift the whole series."""
    assert parse_when("2026-05-01") == datetime(2026, 5, 1, tzinfo=timezone.utc)
    assert parse_when("2026-05-01T10:30:00Z") == parse_when("2026-05-01T10:30:00+00:00")
    assert parse_when("2026-05-01T12:30:00+02:00").hour == 10


def test_series_includes_both_ends_and_rejects_an_inverted_range():
    start, end = parse_when("2026-05-01T00:00:00Z"), parse_when("2026-05-01T02:00:00Z")
    stamps = build_timestamps(start, end, timedelta(hours=1))
    assert len(stamps) == 3                                  # 00, 01 and 02 h
    assert stamps[0] == int(start.timestamp() * 1000)
    assert stamps[-1] == int(end.timestamp() * 1000)
    try:
        build_timestamps(end, start, timedelta(hours=1))
        raise AssertionError("ValueError was expected")
    except ValueError:
        pass


def test_randomize_value_stays_inside_the_deviation_and_never_goes_negative():
    rng = random.Random(1)
    values = [randomize_value(100, 0.15, rng) for _ in range(500)]
    assert all(85 <= v <= 115 for v in values)
    assert min(values) < 100 < max(values)                   # it really does vary
    # mean 0 = a sensor at zero, and it stays at zero (unlike the original generator,
    # which gives a 5% chance of a 1)
    assert randomize_value(0, 0.15, rng) == 0


def test_random_smartspot_generates_entities_x_instants_with_coherent_windows():
    stamps = build_timestamps(parse_when("2026-05-01T00:00:00Z"),
                              parse_when("2026-05-01T05:00:00Z"), timedelta(hours=1))
    messages = generate_random_smartspot_messages(stamps, mean=120, deviation=0.15,
                                                  entities=4, prefix="ss_",
                                                  rng=random.Random(42))
    assert len(messages) == 6 * 4
    assert {m["device_id"] for m in messages} == {f"ss_{n}" for n in range(1, 5)}
    assert {m["timestamp_ms"] for m in messages} == set(stamps)
    for m in messages:
        medium = m["peopleCountMediumInterval"]
        assert 102 <= medium <= 138                                  # 120 +-15%
        # the three windows are the same people counted over 1/5/10 min: a short
        # window above the long one would be impossible
        assert m["peopleCountShortInterval"] <= medium <= m["peopleCountLongInterval"]


def test_random_lidar_publishes_one_entity_set_per_window_with_the_aforo_around_the_mean():
    """Each instant is one aggregation WINDOW, not one detection: what comes out is the
    entities the ingestion would publish for it. `mean` is the average number of
    SIMULTANEOUS people per sensor, so it lands on the aforo, not on any count."""
    stamps = build_timestamps(parse_when("2026-05-01T00:00:00Z"),
                              parse_when("2026-05-01T00:05:00Z"), timedelta(seconds=60))
    messages = generate_random_lidar_messages(stamps, mean=3, deviation=0.15, entities=2,
                                              prefix="obj_", rng=random.Random(42))

    per_window = {}
    for m in messages:
        per_window.setdefault(m["_timeStampMs"], []).append((m["_entityType"], m["_entityId"]))
    assert set(per_window) == set(stamps)
    for entities in per_window.values():
        assert len(entities) == len(set(entities))       # one sample per entity per window
        # 1 zone + 2 sensors x (Observed + Device)
        assert len(entities) == 5

    aforos = [m["totalConcurrentMax"] for m in messages
              if m["_entityType"].endswith("Observed")]
    assert aforos and all(2 <= aforo <= 4 for aforo in aforos)   # 3 +-15%, per sensor


def test_the_same_seed_generates_the_same_series():
    stamps = build_timestamps(parse_when("2026-05-01T00:00:00Z"),
                              parse_when("2026-05-01T03:00:00Z"), timedelta(hours=1))
    kwargs = dict(mean=100, deviation=0.2, entities=3, prefix="ss_")
    first = generate_random_smartspot_messages(stamps, rng=random.Random(7), **kwargs)
    second = generate_random_smartspot_messages(stamps, rng=random.Random(7), **kwargs)
    assert first == second


def test_dates_in_the_future_are_not_clamped_to_now():
    """Generating data ahead of the clock is legitimate (pre-loading a demo)."""
    future = datetime.now(timezone.utc) + timedelta(days=30)
    stamps = build_timestamps(future, future + timedelta(hours=2), timedelta(hours=1))
    messages = generate_random_smartspot_messages(stamps, mean=50, deviation=0.1, entities=1,
                                                  prefix="ss_", rng=random.Random(1))
    assert len(messages) == 3
    assert all(m["timestamp_ms"] > datetime.now(timezone.utc).timestamp() * 1000
               for m in messages)


def test_no_published_attribute_collides_with_a_mandatory_column():
    """The job identifies columns CASE-INSENSITIVELY and the last match wins, so an
    attribute named like urn/type/timestamp in any casing silently replaces it and every
    value ends up dated wrong. It happened: OTEDetection carried a `timeStamp` property in
    ms, which had to be dropped by hand. Checked over every entity, not just one."""
    mandatory = {"urn", "type", "timestamp"}
    for msg in generate_fake_lidar_messages(BASE_TS_MS):
        row = build_csv_row(post_measures.transform_lidar(msg), "lidar")
        lowered = [column.lower() for column in row]
        assert len(lowered) == len(set(lowered))                  # no casing duplicates
        assert mandatory.issubset(row)
        assert [c for c in lowered if c in mandatory] == sorted(mandatory, key=lowered.index)
        assert row["timestamp"] == "2025-10-09T08:53:20Z"


def test_csv_row_flattens_the_geo_and_serializes_the_lists():
    """latitude/longitude flat (same convention as etl/crowd/transform.py, the bulk
    import has no confirmed encoding for a GeoProperty) and absorbedObjectIds as JSON,
    which the parser turns back into a list."""
    msg = dict(generate_fake_smartspot_messages(BASE_TS_MS)[0], device_id="SS1")
    with patch("crowd_predictions.smartspot_transform.smartspot_location", return_value=(10.045, 20.066)):
        entity = post_measures.transform_smartspot_observed(msg)
    row = build_csv_row(entity, "smartspot")
    assert (row["latitude"], row["longitude"]) == (10.045, 20.066)
    assert "location" not in row and "_timeStampMs" not in row

    # The zone entity carries the transit matrix as a JSON string in ONE cell: an
    # attribute per pair would be hundreds of columns with a few dozen sensors.
    zone = next(m for m in generate_fake_lidar_messages(BASE_TS_MS)
                if m["_entityType"].endswith("Zone"))
    row = build_csv_row(post_measures.transform_lidar(zone), "lidar")
    assert json.loads(row["transitions"]) == {}      # sensors that share nobody
    assert all(not isinstance(value, dict) for value in row.values())


def test_csv_columns_are_the_union_of_the_chunk_not_those_of_the_first_row(tmp_path):
    """Not every entity carries the same columns (an unknown device has no
    latitude/longitude): the missing cells go out empty and the parser skips them."""
    rows = [
        {"urn": "urn:ngsi-ld:CrowdFlowObserved:a", "type": "CrowdFlowObserved",
         "timestamp": "2026-05-01T00:00:00Z", "peopleCountMediumInterval": 10},
        {"urn": "urn:ngsi-ld:CrowdFlowObserved:b", "type": "CrowdFlowObserved",
         "timestamp": "2026-05-01T00:00:00Z", "peopleCountMediumInterval": 20,
         "latitude": 43.5, "longitude": -5.6},
    ]
    path = write_csv_chunk(rows, tmp_path / "chunk.csv")
    with open(path, newline="", encoding="utf-8") as handle:
        parsed = list(csv.DictReader(handle))

    assert list(parsed[0])[:3] == ["urn", "type", "timestamp"]
    assert "latitude" in parsed[0] and parsed[0]["latitude"] == ""   # empty, not "None"
    assert parsed[1]["latitude"] == "43.5"


def test_batch_splits_into_chunks_of_batch_size_and_publishes_one_job_per_chunk(tmp_path):
    stamps = build_timestamps(parse_when("2026-05-01T00:00:00Z"),
                              parse_when("2026-05-01T09:00:00Z"), timedelta(hours=1))
    messages = generate_random_smartspot_messages(stamps, mean=100, deviation=0.1, entities=3,
                                                   prefix="ss_", rng=random.Random(3))
    assert len(messages) == 30

    with patch("crowd_predictions.helpers.uploader.upload_csv_via_s3_and_queue", return_value=True) as mock_upload:
        n_ok, total = post_batch(messages, "smartspot", batch_size=10,
                                 tenant="demo_tenant", scope="/", csv_dir=str(tmp_path))

    assert (n_ok, total) == (3, 3)
    assert mock_upload.call_count == 3
    assert len(list(tmp_path.glob("*.csv"))) == 3
    # the tenant/scope of the run reach the queue message
    assert mock_upload.call_args.kwargs == {"tenant": "demo_tenant", "scope": "/"}
    # every row carries its urn: the job reads it PER ROW, it does not use the one in
    # the queue message
    with open(sorted(tmp_path.glob("*.csv"))[0], newline="", encoding="utf-8") as handle:
        chunk = list(csv.DictReader(handle))
    assert len(chunk) == 10
    assert {r["urn"] for r in chunk} == {f"urn:ngsi-ld:CrowdFlowObserved:ss_{n}" for n in (1, 2, 3)}


def test_batch_dry_run_writes_the_csvs_without_publishing_anything(tmp_path):
    messages = generate_fake_smartspot_messages(BASE_TS_MS)
    with patch("crowd_predictions.helpers.uploader.upload_csv_via_s3_and_queue") as mock_upload:
        n_ok, total = post_batch(messages, "smartspot", batch_size=2,
                                 csv_dir=str(tmp_path), dry_run=True)
    assert (n_ok, total) == (2, 2)
    assert mock_upload.call_count == 0
    assert len(list(tmp_path.glob("*.csv"))) == 2


def test_batch_skips_the_unsupported_messages_instead_of_failing(tmp_path):
    valid = generate_fake_lidar_messages(BASE_TS_MS)
    messages = [{"sin": "tipo ni id"}] + valid
    with patch("crowd_predictions.helpers.uploader.upload_csv_via_s3_and_queue", return_value=True) as mock_upload:
        n_ok, total = post_batch(messages, "lidar", batch_size=1000, csv_dir=str(tmp_path))
    assert (n_ok, total) == (1, 1)
    with open(next(iter(tmp_path.glob("*.csv"))), newline="", encoding="utf-8") as handle:
        assert len(list(csv.DictReader(handle))) == len(valid)   # the unusable one is skipped
    assert mock_upload.call_count == 1


def test_random_mode_needs_a_mean():
    """Without --mean there is nothing to generate around: better an error than a
    series of zeros published in an environment."""
    stderr = io.StringIO()
    with patch("sys.argv", ["post_measures.py", "--source", "smartspot", "--mode", "random",
                            "--dry-run"]), contextlib.redirect_stderr(stderr):
        try:
            post_measures.main()
            raise AssertionError("SystemExit was expected")
        except SystemExit as exc:
            assert exc.code == 2
    assert "--mean" in stderr.getvalue()


def test_max_messages_stops_an_absurd_volume_before_generating_it():
    """A year at 1 s is 31.5 M measures; the guard has to catch it from the count, with
    no list built.

    It USED TO take 12 s: the estimate read `len(stamps)`, so the instants were
    materialized before the guard that exists to avoid materializing them. The test
    passed all the same - it was measuring the cost, not the guard. If it goes slow
    again, the arithmetic count went back to being a build."""
    argv = ["post_measures.py", "--source", "smartspot", "--mode", "random", "--mean", "100",
            "--from", "2026-01-01T00:00:00Z", "--to", "2026-12-31T00:00:00Z",
            "--interval", "1s", "--dry-run"]
    with patch("sys.argv", argv), patch("builtins.print") as mock_print, \
            patch("crowd_predictions.fake_measures.generate_random_smartspot_messages") as mock_generate:
        try:
            post_measures.main()
            raise AssertionError("SystemExit was expected")
        except SystemExit as exc:
            assert exc.code == 1
    output = " ".join(str(a) for call in mock_print.call_args_list for a in call.args)
    assert "--max-messages" in output
    assert mock_generate.call_count == 0


@pytest.mark.parametrize("hours, step_s", [(1, 60), (3, 900), (24, 3600), (0, 60)])
def test_the_estimated_count_is_the_one_that_would_be_built(hours, step_s):
    """`count_timestamps` guards a volume that `build_timestamps` then produces. If the
    two drift apart the guard lets through, or rejects, the wrong thing."""
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(hours=hours)
    step = timedelta(seconds=step_s)

    assert count_timestamps(start, end, step) == len(build_timestamps(start, end, step))


def test_random_mode_defaults_to_the_batch_route():
    """A series of thousands of measures over the IoT Agent (one POST each, and it
    loses data under load) is never what you want."""
    argv = ["post_measures.py", "--source", "smartspot", "--mode", "random", "--mean", "100",
            "--from", "2026-05-01T00:00:00Z", "--to", "2026-05-01T05:00:00Z",
            "--interval", "1h", "--dry-run"]
    with patch("sys.argv", argv), patch("crowd_predictions.fake_measures.post_batch",
                                        return_value=(1, 1)) as mock_batch, \
            patch("crowd_predictions.fake_measures.post_measure") as mock_post, \
            patch("builtins.print"):
        try:
            post_measures.main()
        except SystemExit as exc:
            assert exc.code == 0
    assert mock_batch.call_count == 1
    assert mock_post.call_count == 0
    assert len(mock_batch.call_args.args[0]) == 6 * post_measures.DEFAULT_ENTITIES


def test_fixture_mode_keeps_the_iota_route():
    """What the script did before must not change route on its own."""
    with patch("sys.argv", ["post_measures.py", "--source", "lidar", "--dry-run"]), \
            patch("crowd_predictions.fake_measures.post_batch") as mock_batch, \
            patch("builtins.print"):
        post_measures.main()
    assert mock_batch.call_count == 0


def test_batch_route_requires_the_queue_url_not_the_iot_agent_one():
    with patch.dict(os.environ, {"IOTA_URL": "http://iota", "IOTA_SMARTSPOT_APIKEY": "k"},
                    clear=True), \
            patch("sys.argv", ["post_measures.py", "--source", "smartspot",
                               "--route", "batch"]), \
            patch("builtins.print") as mock_print:
        try:
            post_measures.main()
            raise AssertionError("SystemExit was expected")
        except SystemExit as exc:
            assert exc.code == 1
    output = " ".join(str(a) for call in mock_print.call_args_list for a in call.args)
    assert "QUEUES_CONSUMER_API_URL" in output


def test_sources_declare_distinct_apikey_and_prefix_variables():
    """lidar and smartspot are different IoT Agent service groups: each one with its
    own apikey. Mixing them makes the IoT Agent reject or misroute the measure."""
    lidar, smartspot = post_measures.SOURCES["lidar"], post_measures.SOURCES["smartspot"]
    assert lidar["apikey_env"] == "IOTA_LIDAR_APIKEY"
    assert smartspot["apikey_env"] == "IOTA_SMARTSPOT_APIKEY"
    assert lidar["prefix_env"] == "TEST_ENTITY_PREFIX"
    assert smartspot["prefix_env"] == "TEST_SMARTSPOT_PREFIX"
