"""
Notifications that reach Timescale after their hour was cached.

The cache deletes each hour from Timescale once its CSV is uploaded, so what is
left there for a closed hour is exactly what arrived late. The periodic run
re-reads the closed hours of a lookback window and the load merges those rows
into the existing CSV instead of overwriting it.
"""

import io
import os
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from etls.data_cache.crowd_data_cache_etl.load import crowd_data_cache_load as load_module
from etls.data_cache.crowd_data_cache_etl.load.crowd_data_cache_load import (
    CrowdDataCacheLoad,
    _is_not_found,
)
from helpers.crowd.crowd_utils import CROWD_CACHE_COLUMNS, to_crowd_cache_schema
from jobs.data_cache import all_data_cache_crowd_jobs as job_module
from jobs.data_cache.all_data_cache_crowd_jobs import DataCacheCrowdAll
from schemas.crowd_data_cache_etl_request_schema import (
    AllCrowdDataCacheETLRequest,
    CrowdDataCacheETLEntity,
    CrowdDataCacheETLRequest,
)
from tasks import data_cache as data_cache_tasks

URN = "urn:ngsi-ld:CrowdFlowEvent:SPT94C354C4C5504A66106F0E2B_CFE"
S3_KEY = "data_cache/crowd/tenant/_/SPT94C354C4C5504A66106F0E2B_CFE/2026-11-02T10_00_00_to_2026-11-02T11_00_00.csv"


class _NotFound(Exception):
    def __init__(self):
        self.response = {"Error": {"Code": "404"}}


class FakeStorage:
    """In-memory bucket with the download/upload contract of S3Storage."""

    def __init__(self, tmp_path, objects=None, download_error=None):
        self.tmp = tmp_path
        self.objects = dict(objects or {})
        self.download_error = download_error

    def download_file(self, filename, path):
        if self.download_error:
            raise self.download_error
        if path not in self.objects:
            raise _NotFound()
        local = os.path.join(self.tmp, filename)
        with open(local, "w") as f:
            f.write(self.objects[path])
        return local

    def upload_file(self, filename, path):
        with open(path) as f:
            self.objects[filename] = f.read()
        return path


def _request():
    return CrowdDataCacheETLRequest(
        user_id=1,
        entities=[CrowdDataCacheETLEntity(id=1, tenant="tenant", scope="/", urn=URN)],
        start_date="2026-11-02T10:00:00",
        end_date="2026-11-02T11:00:00",
    )


def _rows(*detections):
    return to_crowd_cache_schema(
        pd.DataFrame(
            [
                {"timeinstant": t, "entityId": URN, "visitorId": v, "detectionType": 2,
                 "random": 1, "rssi": -70, "fields": f}
                for t, v, f in detections
            ]
        )
    )


def _load(df, storage, tmp_path, delete=False):
    item = {
        "urn": URN, "df": df, "s3_prefix": S3_KEY,
        "filename": "2026-11-02T10_00_00_to_2026-11-02T11_00_00.csv",
        "tenant": "tenant", "scope": "_", "urn_split": "SPT94C354C4C5504A66106F0E2B_CFE",
    }
    loader = CrowdDataCacheLoad(
        request=_request(),
        transform_output={"result": [item], "variables": ["cfeBlock"]},
        main_db=MagicMock(),
        realtime_db=MagicMock(),
    )
    with patch.object(load_module, "storage", storage), \
         patch.object(load_module, "TEMP_DIR", str(tmp_path / "temp")), \
         patch.object(load_module.settings, "DATA_CACHE_DELETE_AFTER_UPLOAD", delete), \
         patch.object(load_module.aether_link_helper, "delete_time_series") as delete_ts:
        loader.load()
    return delete_ts


def test_late_rows_are_merged_into_the_existing_hour(tmp_path):
    cached = _rows(("2026-11-02T10:05:00", "vA", None), ("2026-11-02T10:10:00", "vB", None))
    storage = FakeStorage(tmp_path, {S3_KEY: cached.to_csv(index=False)})

    _load(_rows(("2026-11-02T10:58:00", "vC", '[{"type":1}]')), storage, tmp_path)

    out = pd.read_csv(io.StringIO(storage.objects[S3_KEY]))
    assert list(out.columns) == CROWD_CACHE_COLUMNS
    assert out["visitorId"].tolist() == ["vA", "vB", "vC"]


def test_rerun_of_the_same_hour_does_not_duplicate(tmp_path):
    cached = _rows(("2026-11-02T10:05:00", "vA", '[{"type":255}]'), ("2026-11-02T10:06:00", "vB", None))
    storage = FakeStorage(tmp_path, {S3_KEY: cached.to_csv(index=False)})

    _load(cached, storage, tmp_path)

    out = pd.read_csv(io.StringIO(storage.objects[S3_KEY]))
    assert out["visitorId"].tolist() == ["vA", "vB"]


def test_repeated_reports_of_a_visitor_are_all_kept(tmp_path):
    """
    Each report repeats the visitor with the same first-seen timeinstant and its
    latest RSSI: they are distinct rows, not duplicates (the merge once dropped
    ~80 % of an hour treating them as such).
    """
    repeats = _rows(("2026-11-02T10:05:00", "vA", None), ("2026-11-02T10:05:00", "vA", None))
    repeats.loc[1, "rssi"] = -91
    repeats.loc[2] = repeats.loc[0]  # an exact repeat, also a real report
    storage = FakeStorage(tmp_path, {S3_KEY: repeats.to_csv(index=False)})

    _load(_rows(("2026-11-02T10:05:00", "vA", None), ("2026-11-02T10:59:00", "vZ", None)), storage, tmp_path)

    out = pd.read_csv(io.StringIO(storage.objects[S3_KEY]))
    assert len(out) == 4
    assert out["visitorId"].tolist().count("vA") == 3


def test_old_layout_file_is_upgraded_when_merged(tmp_path):
    old_layout = (
        "timeinstant,entityId,israndommac,visitorid,detectiontype,rssi,ssid,signature\n"
        f"2026-11-02 10:05:00,{URN},1.0,vA,2.0,-70.0,,\n"
    )
    storage = FakeStorage(tmp_path, {S3_KEY: old_layout})

    _load(_rows(("2026-11-02T10:50:00", "vC", None)), storage, tmp_path)

    out = pd.read_csv(io.StringIO(storage.objects[S3_KEY]))
    assert list(out.columns) == CROWD_CACHE_COLUMNS
    assert out["visitorId"].tolist() == ["vA", "vC"]
    assert out["random"].tolist() == [1, 1]


def test_storage_error_other_than_missing_keeps_file_and_timescale(tmp_path):
    cached = _rows(("2026-11-02T10:05:00", "vA", None)).to_csv(index=False)
    storage = FakeStorage(tmp_path, {S3_KEY: cached}, download_error=RuntimeError("throttled"))

    delete_ts = _load(_rows(("2026-11-02T10:50:00", "vC", None)), storage, tmp_path, delete=True)

    assert storage.objects[S3_KEY] == cached
    delete_ts.assert_not_called()


def test_first_write_of_an_hour_deletes_from_timescale_when_enabled(tmp_path):
    storage = FakeStorage(tmp_path)

    delete_ts = _load(_rows(("2026-11-02T10:05:00", "vA", None)), storage, tmp_path, delete=True)

    assert S3_KEY in storage.objects
    delete_ts.assert_called_once()


@pytest.mark.parametrize(
    "error, expected",
    [
        (_NotFound(), True),
        (SimpleNamespace(code="NoSuchKey"), True),
        (RuntimeError("timeout"), False),
        (SimpleNamespace(response={"Error": {"Code": "403"}}), False),
    ],
)
def test_is_not_found(error, expected):
    assert _is_not_found(error) is expected


def test_empty_read_gives_an_empty_cache_frame():
    out = to_crowd_cache_schema(pd.DataFrame())

    assert out.empty and list(out.columns) == CROWD_CACHE_COLUMNS


def _dispatched_windows(request, lookback):
    entities = [SimpleNamespace(id=1, urn=URN)]
    with patch.object(job_module, "get_organization_admins", return_value=[SimpleNamespace(id=7)]), \
         patch.object(job_module, "get_entities_with_permissions", return_value=[(e, "/", "tenant") for e in entities]), \
         patch.object(job_module.settings, "DATA_CACHE_CROWD_LOOKBACK_HOURS", lookback), \
         patch.object(job_module, "datetime") as fake_dt, \
         patch.object(data_cache_tasks.data_cache_crowd_job, "delay") as delay:
        fake_dt.now.return_value = datetime(2026, 11, 2, 13, 8)
        DataCacheCrowdAll(request=request, db=MagicMock()).handle()
    return [(c.args[0].start_date.hour, c.args[0].force) for c in delay.call_args_list]


def test_periodic_run_sweeps_the_lookback_hours_forced():
    windows = _dispatched_windows(AllCrowdDataCacheETLRequest(start_date=None, end_date=None), lookback=3)

    # 12:00-13:00 is the new hour; 9, 10 and 11 are re-read for late rows
    assert windows == [(9, True), (10, True), (11, True), (12, False)]


def test_explicit_range_is_not_widened():
    request = AllCrowdDataCacheETLRequest(
        start_date=datetime(2026, 11, 1, 5), end_date=datetime(2026, 11, 1, 7), force=False
    )

    assert _dispatched_windows(request, lookback=24) == [(5, False), (6, False)]
