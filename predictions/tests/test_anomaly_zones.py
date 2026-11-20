"""
anomaly_detection/zones.py - the daily scoring of the fused zone occupancy.

No network: Aether is replaced by a function returning its long rows, storage by
the in-memory one of test_anomaly_pipeline.py, and the importation by a fake that
keeps the csvs it was given. The scoring core runs for real.
"""

import json
import math
import os
import random
from datetime import datetime, timedelta
from unittest.mock import patch

import pandas as pd

from crowd_predictions.anomaly_detection import zones

from test_anomaly_pipeline import _MemoryStorage

ZONE_A = "urn:ngsi-ld:CrowdFlowZone:Z01"
ZONE_B = "urn:ngsi-ld:CrowdFlowZone:Z02"
NOW = datetime(2026, 3, 20, 5, 30)


def _config(measures=("occupancy",)) -> dict:
    return {"ANOMALY_CONFIG": json.dumps(
        {"CrowdFlowZone": {"measures": list(measures), "cadence_minutes": 60,
                           "calendar": ["hour", "weekday"], "rolling_hours": 2}})}


def _aether_rows(zones_, start, end, spike_at=None, seed=1):
    """Hourly occupancy per zone between start and end, as Aether returns it (long, ISO
    timestamps with an offset). A daily profile with noise; `spike_at` gets 20x."""
    rng = random.Random(seed)
    rows = []
    t = start
    while t < end:
        for zone in zones_:
            value = 40 * math.sin(math.pi * t.hour / 24) ** 2 + 5 + rng.uniform(-2, 2)
            if spike_at is not None and t == spike_at and zone == ZONE_A:
                value *= 20
            rows.append({"timestamp": t.isoformat() + "+00:00", "device_id": zone,
                         "measure_name": "occupancy", "value": round(value, 2)})
        t += timedelta(hours=1)
    return pd.DataFrame(rows)


class _Published:
    """Stands in for upload_csv_files: keeps every csv it is handed, as a DataFrame."""

    def __init__(self):
        self.frames = {}

    def __call__(self, paths):
        for path in paths:
            self.frames[os.path.basename(path)] = pd.read_csv(path)
        return {"successful": list(paths), "failed": []}


def _score(tmp_path, storage, rows, now=NOW, published=None, env=None):
    published = published or _Published()
    with patch.dict(os.environ, env if env is not None else _config(), clear=False), \
         patch.object(zones, "resolve_zone_ids", return_value=[ZONE_A, ZONE_B]), \
         patch.object(zones.aether, "get_time_series_as_dataframe", return_value=rows) as query, \
         patch.object(zones, "get_storage", return_value=storage), \
         patch.object(zones, "upload_csv_files", published):
        code = zones.score_zones(str(tmp_path / "out"), now=now)
    return code, published, query


# --- The window -------------------------------------------------------------------

def test_the_window_is_the_last_closed_days_never_the_one_in_progress():
    with patch.dict(os.environ, {"ANOMALY_LOOKBACK_DAYS": "3"}):
        start, end = zones.scoring_window(NOW)

    assert end == datetime(2026, 3, 20, 0, 0)
    assert start == datetime(2026, 3, 17, 0, 0)


def test_the_query_asks_for_the_window_and_the_configured_measures(tmp_path):
    _code, _published, query = _score(tmp_path, _MemoryStorage(), pd.DataFrame())

    kwargs = query.call_args.kwargs
    assert kwargs["device_ids"] == [ZONE_A, ZONE_B]
    assert kwargs["measure_ids"] == ["occupancy"]
    assert kwargs["start_date"] == "2026-03-17T00:00:00"
    assert kwargs["end_date"] == "2026-03-20T00:00:00"


# --- Long rows to points ----------------------------------------------------------

def test_points_are_one_per_zone_and_hour_in_naive_utc():
    rows = _aether_rows([ZONE_A], datetime(2026, 3, 19, 0), datetime(2026, 3, 19, 3))
    points = zones.zone_points(rows, ["occupancy"])

    assert [p["timestamp"] for p in points] == [datetime(2026, 3, 19, h) for h in range(3)]
    assert all(p["entity_id"] == ZONE_A for p in points)
    assert all(isinstance(p["raw_measures"]["occupancy"], float) for p in points)


def test_an_hour_missing_a_measure_is_skipped_not_filled_in():
    rows = pd.DataFrame([
        {"timestamp": "2026-03-19T00:00:00Z", "device_id": ZONE_A, "measure_name": "occupancy", "value": 10},
        {"timestamp": "2026-03-19T00:00:00Z", "device_id": ZONE_A, "measure_name": "confidence", "value": 1},
        {"timestamp": "2026-03-19T01:00:00Z", "device_id": ZONE_A, "measure_name": "occupancy", "value": 12},
    ])
    points = zones.zone_points(rows, ["occupancy", "confidence"])

    assert [p["timestamp"] for p in points] == [datetime(2026, 3, 19, 0)]


def test_non_numeric_values_and_empty_reads_give_no_points():
    rows = pd.DataFrame([{"timestamp": "2026-03-19T00:00:00Z", "device_id": ZONE_A,
                          "measure_name": "occupancy", "value": "n/a"}])
    assert zones.zone_points(rows, ["occupancy"]) == []
    assert zones.zone_points(pd.DataFrame(), ["occupancy"]) == []


# --- Scoring and publishing ---------------------------------------------------------

def test_off_when_the_zone_datamodel_is_not_configured(tmp_path):
    code, published, query = _score(tmp_path, _MemoryStorage(), pd.DataFrame(),
                                    env={"ANOMALY_CONFIG": json.dumps({"Other": {"measures": ["m"]}})})

    assert code == 0
    query.assert_not_called()
    assert published.frames == {}


def test_no_readings_is_not_a_failure(tmp_path):
    code, published, _query = _score(tmp_path, _MemoryStorage(), pd.DataFrame())

    assert code == 0
    assert published.frames == {}


def test_every_scored_hour_is_published_on_its_own_zone(tmp_path):
    start, end = datetime(2026, 3, 17), datetime(2026, 3, 20)
    code, published, _query = _score(tmp_path, _MemoryStorage(), _aether_rows([ZONE_A, ZONE_B], start, end))

    assert code == 0
    assert sorted(published.frames) == [f"{ZONE_A}.csv", f"{ZONE_B}.csv"]
    out = published.frames[f"{ZONE_A}.csv"]
    assert list(out.columns) == ["urn", "type", "timestamp", "isOutlier"]
    assert set(out["urn"]) == {ZONE_A}
    assert set(out["type"]) == {"CrowdFlowZone"}
    assert len(out) == 72
    assert out["timestamp"].iloc[0] == "2026-03-17T00:00:00.000000Z"
    assert set(out["isOutlier"]) <= {0, 1}


def test_a_sudden_spike_is_flagged_once_the_zone_has_learnt_its_normal(tmp_path):
    storage = _MemoryStorage()
    learn_start = datetime(2026, 2, 1)
    # Six weeks of normal days, scored day by day as the CronJob would.
    for day in range(42):
        day_start = learn_start + timedelta(days=day)
        rows = _aether_rows([ZONE_A, ZONE_B], day_start, day_start + timedelta(days=1), seed=day)
        assert _score(tmp_path, storage, rows, now=day_start + timedelta(days=1, hours=5))[0] == 0

    spike = learn_start + timedelta(days=42, hours=13)
    day_start = learn_start + timedelta(days=42)
    rows = _aether_rows([ZONE_A, ZONE_B], day_start, day_start + timedelta(days=1), spike_at=spike, seed=99)
    _code, published, _query = _score(tmp_path, storage, rows, now=day_start + timedelta(days=1, hours=5))

    out = published.frames[f"{ZONE_A}.csv"]
    flagged = out[out["isOutlier"] == 1]["timestamp"].tolist()
    assert spike.strftime(zones.TIMESTAMP_FORMAT) in flagged
    # The spike and the two hours after it, while it is still inside the 2 h volatility
    # window (rolling_hours) - not the rest of the day.
    assert len(flagged) <= 3
    # The other zone had a normal day.
    other = published.frames[f"{ZONE_B}.csv"]
    assert (other["isOutlier"] == 1).sum() <= 1


def test_a_rerun_of_the_same_days_does_not_learn_them_twice(tmp_path):
    storage = _MemoryStorage()
    start, end = datetime(2026, 3, 17), datetime(2026, 3, 20)
    rows = _aether_rows([ZONE_A, ZONE_B], start, end)

    _score(tmp_path, storage, rows)
    model_after_first = {k: v for k, v in storage.files.items() if "/models/" in k}
    _score(tmp_path, storage, rows)
    model_after_rerun = {k: v for k, v in storage.files.items() if "/models/" in k}

    assert model_after_first
    assert model_after_rerun == model_after_first


def test_a_failed_publication_turns_the_run_red(tmp_path):
    start, end = datetime(2026, 3, 17), datetime(2026, 3, 20)

    def failing(paths):
        return {"successful": [], "failed": list(paths)}

    code, _published, _query = _score(tmp_path, _MemoryStorage(), _aether_rows([ZONE_A], start, end),
                                      published=failing)
    assert code == 1


def test_the_pipeline_runs_the_zones_before_the_folder_sweep():
    from crowd_predictions.anomaly_detection import pipeline

    calls = []
    with patch.object(pipeline, "score_zones", side_effect=lambda _dir: calls.append("zones") or 0), \
         patch.object(pipeline, "sweep_folder", side_effect=lambda *_: calls.append("sweep") or 0):
        assert pipeline.run_one("demo", "/") == 0

    assert calls == ["zones", "sweep"]
