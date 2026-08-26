"""
anomaly_detection/pipeline.py - the CronJob that sweeps the storage folder.

No network and no real storage: _MemoryStorage implements the StorageType contract
in memory. Everything here is a made-up datamodel with made-up measures, on purpose -
the vertical must not know what a zone is.
"""

import json
import math
import os
import random
from datetime import datetime, timedelta
from unittest.mock import patch

import pandas as pd

from crowd_predictions.anomaly_detection import pipeline
from crowd_predictions.anomaly_detection import storage as anomaly_storage

ENV = {"FIWARE_TENANT": "demo", "FIWARE_SCOPE": "/"}
ROOT = "anomalies_detection/demo/_"
T0 = datetime(2026, 1, 1, 0, 0)


class _MemoryStorage:
    def __init__(self):
        self.files = {}

    def upload_file(self, key, path):
        with open(path, "rb") as f:
            self.files[key] = f.read()
        return path

    def download_file(self, key, path):
        if key not in self.files:
            raise FileNotFoundError(key)
        with open(path, "wb") as f:
            f.write(self.files[key])
        return path

    def delete_file(self, key):
        self.files.pop(key, None)

    def list_prefix(self, prefix):
        return [k for k in self.files if k.startswith(prefix)]


def _config(datamodel="Example", measures=None, calendar=("hour",), cadence=60) -> dict:
    entry = {"cadence_minutes": cadence, "calendar": list(calendar)}
    if measures is not None:
        entry["measures"] = list(measures)
    return {**ENV, "ANOMALY_CONFIG": json.dumps({datamodel: entry})}


def _rows(n=200, datamodel="Example", entity="urn:ngsi-ld:Example:E1", extra=None, seed=1,
          start_hour=1, second_measure=False):
    """A daily profile with noise, in import (wide) format."""
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        ts = T0 + timedelta(hours=i + start_hour)
        row = {"timestamp": ts.isoformat() + "Z", "urn": entity, "type": datamodel,
               "m1": round(max(0.0, 50 * math.sin(math.pi * ts.hour / 24) ** 2
                               + rng.uniform(-3, 3)), 2)}
        if second_measure:
            # Has to VARY: a constant column is dropped as carrying no information
            # (that filter is what caught `serialNumber` on a real export).
            row["m2"] = round(2.0 + rng.uniform(-0.5, 0.5), 3)
        row.update(extra or {})
        rows.append(row)
    return rows


def _put_csv(storage, rows, name="serie.csv", tmp_path=None, key=None):
    path = os.path.join(str(tmp_path), name)
    pd.DataFrame(rows).to_csv(path, index=False)
    storage.upload_file(key or f"{ROOT}/{name}", path)
    return key or f"{ROOT}/{name}"


def _processed(storage, name="serie.csv", tmp_path=None) -> pd.DataFrame:
    path = os.path.join(str(tmp_path), f"read_{name}")
    storage.download_file(f"{ROOT}/processed/{name}", path)
    return pd.read_csv(path)


def _run(storage):
    with patch("crowd_predictions.anomaly_detection.pipeline.get_storage", return_value=storage):
        return pipeline.run_one("demo", "/")


# --- The normal states ----------------------------------------------------------

def test_an_empty_folder_does_nothing_and_is_not_a_failure():
    """The state of most runs: the CronJob fires, nobody left a file, green."""
    storage = _MemoryStorage()
    with patch.dict(os.environ, _config(), clear=False):
        assert _run(storage) == 0
    assert storage.files == {}


def test_a_csv_is_scored_archived_with_its_verdict_and_removed_from_the_inbox(tmp_path):
    storage = _MemoryStorage()
    key = _put_csv(storage, _rows(), tmp_path=tmp_path)
    with patch.dict(os.environ, _config(measures=["m1"]), clear=False):
        assert _run(storage) == 0

    assert key not in storage.files                       # the inbox is emptied
    out = _processed(storage, tmp_path=tmp_path)
    assert "isOutlier" in out.columns
    assert "isStale" not in out.columns                   # deliberately gone
    assert out["isOutlier"].notna().all()


def test_the_model_is_created_on_the_first_run_and_reused_on_the_second(tmp_path):
    storage = _MemoryStorage()
    with patch.dict(os.environ, _config(measures=["m1"]), clear=False):
        _put_csv(storage, _rows(), name="a.csv", tmp_path=tmp_path)
        _run(storage)
        models = [k for k in storage.files if k.endswith(".pkl")]
        assert models == [f"{ROOT}/models/anomaly_Example.pkl"]

        first = storage.files[models[0]]
        # LATER instants: the same ones would be re-scored but not re-learnt (the
        # watermark), and the bundle would be byte-identical - which is the
        # idempotency other tests assert.
        _put_csv(storage, _rows(seed=2, start_hour=500), name="b.csv", tmp_path=tmp_path)
        _run(storage)
    assert storage.files[models[0]] != first              # kept learning, same bundle
    assert len([k for k in storage.files if k.endswith(".pkl")]) == 1


def test_a_contextual_anomaly_is_the_one_that_gets_flagged(tmp_path):
    """The point of the whole thing: a value that is perfectly normal at midday and
    impossible at 04:00 is flagged only in the second case."""
    storage = _MemoryStorage()
    rows = _rows(400)
    at_0400 = T0 + timedelta(days=20, hours=4)
    rows.append({"timestamp": at_0400.isoformat() + "Z", "urn": "urn:ngsi-ld:Example:E1",
                 "type": "Example", "m1": 55.0})
    _put_csv(storage, rows, tmp_path=tmp_path)
    with patch.dict(os.environ, _config(measures=["m1"]), clear=False):
        _run(storage)

    out = _processed(storage, tmp_path=tmp_path)
    assert out["isOutlier"].iloc[-1] == 1
    assert out["isOutlier"].sum() < 10                    # and not everything else


# --- Input discipline -----------------------------------------------------------

def test_only_the_csvs_at_the_root_are_picked_up(tmp_path):
    """models/ and processed/ live underneath: re-reading our own output would teach
    the model its own verdicts."""
    storage = _MemoryStorage()
    _put_csv(storage, _rows(20), name="root.csv", tmp_path=tmp_path)
    _put_csv(storage, _rows(20), key=f"{ROOT}/processed/old.csv", name="old.csv",
             tmp_path=tmp_path)
    with patch.dict(os.environ, _config(measures=["m1"]), clear=False):
        assert pipeline.pending_csv_keys(storage) == [f"{ROOT}/root.csv"]


def test_an_export_format_csv_is_rejected_and_left_in_place(tmp_path):
    """The long format has no `type` column and one row per measurement - it has to
    be converted first, not half-read."""
    storage = _MemoryStorage()
    key = _put_csv(storage, [{"device_id": "urn:ngsi-ld:Example:E1", "measure_id": "m1",
                              "measure_name": "M1", "timestamp": "2026-01-01T00:00:00",
                              "value": 1.0}], tmp_path=tmp_path)
    with patch.dict(os.environ, _config(measures=["m1"]), clear=False):
        assert _run(storage) == 1                         # red: somebody must fix it
    assert key in storage.files                           # and it is still there


def test_a_file_mixing_datamodels_is_rejected(tmp_path):
    """One model per datamodel: mixing them would train one model on two signals."""
    storage = _MemoryStorage()
    key = _put_csv(storage, _rows(10) + _rows(10, datamodel="Other"), tmp_path=tmp_path)
    with patch.dict(os.environ, _config(measures=["m1"]), clear=False):
        assert _run(storage) == 1
    assert key in storage.files


def test_one_broken_file_does_not_stop_the_others(tmp_path):
    storage = _MemoryStorage()
    _put_csv(storage, [{"nonsense": 1}], name="broken.csv", tmp_path=tmp_path)
    _put_csv(storage, _rows(20), name="good.csv", tmp_path=tmp_path)
    with patch.dict(os.environ, _config(measures=["m1"]), clear=False):
        assert _run(storage) == 1                         # red because one failed
    assert f"{ROOT}/broken.csv" in storage.files          # left to be fixed
    assert f"{ROOT}/processed/good.csv" in storage.files  # the other went through


def test_rows_missing_a_measure_are_skipped_never_filled_in(tmp_path):
    """A forward-filled dimension has delta 0 and rolling_std 0 - the exact signature
    of a frozen sensor. Filling would manufacture the anomaly."""
    storage = _MemoryStorage()
    rows = _rows(30)
    rows.append({"timestamp": (T0 + timedelta(hours=99)).isoformat() + "Z",
                 "urn": "urn:ngsi-ld:Example:E1", "type": "Example"})     # no m1
    _put_csv(storage, rows, tmp_path=tmp_path)
    with patch.dict(os.environ, _config(measures=["m1"]), clear=False):
        _run(storage)

    out = _processed(storage, tmp_path=tmp_path)
    assert out["isOutlier"].isna().sum() == 1             # that row got no verdict
    assert out["isOutlier"].notna().sum() == 30           # the rest did


# --- Measure selection ----------------------------------------------------------

def test_only_numeric_columns_become_measures(tmp_path):
    storage = _MemoryStorage()
    rows = _rows(10, extra={"name": "a label", "shape": '{"L1": 3}'})
    _put_csv(storage, rows, tmp_path=tmp_path)
    df = pipeline.read_wide_csv(storage, f"{ROOT}/serie.csv", str(tmp_path))
    assert pipeline.numeric_measures(df, "k") == ["m1"]


def test_a_column_with_one_stray_string_is_not_taken_as_a_measure(tmp_path):
    """Half-reading a column would invent points out of the rows that do parse.

    The string is deliberately NOT one of pandas' null sentinels ("n/a", "NULL",
    ...): those are read as an empty cell, which is a different case - the row is
    skipped and the column stays a measure."""
    storage = _MemoryStorage()
    rows = _rows(10, second_measure=True)
    rows[5]["m2"] = "roto"
    _put_csv(storage, rows, tmp_path=tmp_path)
    df = pipeline.read_wide_csv(storage, f"{ROOT}/serie.csv", str(tmp_path))
    assert pipeline.numeric_measures(df, "k") == ["m1"]


def test_with_no_measures_configured_they_are_auto_detected(tmp_path):
    storage = _MemoryStorage()
    _put_csv(storage, _rows(30, second_measure=True, extra={"name": "x"}), tmp_path=tmp_path)
    with patch.dict(os.environ, _config(measures=None), clear=False):
        assert _run(storage) == 0
        assert anomaly_storage.stored_measure_names(storage, "Example") == ["m1", "m2"]


def test_an_auto_detected_measure_set_is_frozen_by_the_first_run(tmp_path):
    """A later file with one column fewer must NOT redefine the vector: that would
    not degrade the model, it would reset every entity's history at once."""
    storage = _MemoryStorage()
    with patch.dict(os.environ, _config(measures=None), clear=False):
        _put_csv(storage, _rows(30, second_measure=True), name="a.csv", tmp_path=tmp_path)
        _run(storage)
        frozen = anomaly_storage.stored_measure_names(storage, "Example")

        _put_csv(storage, _rows(30), name="b.csv", tmp_path=tmp_path)   # no m2
        _run(storage)
        assert anomaly_storage.stored_measure_names(storage, "Example") == frozen == ["m1", "m2"]

    out = _processed(storage, name="b.csv", tmp_path=tmp_path)
    assert out["isOutlier"].isna().all()   # nothing scorable, but the model survived


def test_configured_measures_win_over_auto_detection(tmp_path):
    storage = _MemoryStorage()
    _put_csv(storage, _rows(30, second_measure=True), tmp_path=tmp_path)
    with patch.dict(os.environ, _config(measures=["m1"]), clear=False):
        _run(storage)
        assert anomaly_storage.stored_measure_names(storage, "Example") == ["m1"]


# --- Storage layout -------------------------------------------------------------

def test_everything_hangs_off_the_tenant_and_scope_folder(tmp_path):
    """Two deployments over one bucket must not read each other's models."""
    storage = _MemoryStorage()
    _put_csv(storage, _rows(20), tmp_path=tmp_path)
    with patch.dict(os.environ, _config(measures=["m1"]), clear=False):
        _run(storage)
    assert all(k.startswith(f"{ROOT}/") for k in storage.files), sorted(storage.files)
    assert any(k.startswith(f"{ROOT}/models/") for k in storage.files)
    assert any(k.startswith(f"{ROOT}/processed/") for k in storage.files)


def test_another_tenant_gets_its_own_folder(tmp_path):
    storage = _MemoryStorage()
    with patch.dict(os.environ, {**_config(measures=["m1"]), "FIWARE_TENANT": "otro"},
                    clear=False):
        _put_csv(storage, _rows(20), key="anomalies_detection/otro/_/serie.csv",
                 tmp_path=tmp_path)
        assert _run(storage) == 0
    assert "anomalies_detection/otro/_/processed/serie.csv" in storage.files
