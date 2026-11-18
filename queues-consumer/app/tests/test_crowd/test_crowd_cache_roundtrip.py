"""
What the crowd data cache writes is what classification and unique visitors read.

The cache is written from Timescale rows (here with the block under r_cfe_block,
as this deployment receives it) and read back with the same calls the two ETLs
make. Right after a deploy one window holds files of both layouts: the old one
(lowercase names for the block's detections) and the fixed one; both are read.
"""

import io
from datetime import datetime
from unittest.mock import patch

import pandas as pd

import helpers.aether_link.aether_link_helper as aether_link_helper
from helpers.crowd.crowd_utils import (
    crowd_df_columns_rename,
    crowd_row_processing_lambda,
    to_crowd_cache_schema,
)

ENTITY = "urn:ngsi-ld:CrowdFlowEvent:SPT0001_CFE"
CACHE_RENAMES = {
    "r_cfe_random": "random",
    "r_cfe_visitorId": "visitorId",
    "r_cfe_detectType": "detectionType",
    "r_cfe_timeinstant": "timeinstant",
    "r_cfe_rssi": "rssi",
    "r_cfe_ssid": "ssid",
    "r_cfe_signature": "signature",
}
# 2026-11-02 10:05:00 UTC
T0 = 1793613900


def _detection(offset, visitor):
    return {"r_cfe_timeinstant": T0 + offset, "r_cfe_detectType": 2, "r_cfe_random": 0,
            "r_cfe_visitorId": visitor, "r_cfe_rssi": -80,
            "r_cfe_fields": [{"type": 1, "length": 1, "data": "Bg=="}]}


def _written_csv():
    """One hour as the cache writes it now: a list block and a single-detection block."""
    timescale_rows = pd.DataFrame(
        [
            {"timeinstant": "2026-11-02T10:06:00", "entityId": ENTITY,
             "r_cfe_block": [_detection(0, "vA"), _detection(30, "vB")]},
            {"timeinstant": "2026-11-02T10:16:00", "entityId": ENTITY,
             "r_cfe_block": _detection(600, "vC")},
        ]
    )
    df = crowd_row_processing_lambda(timescale_rows, CACHE_RENAMES, keep_unmapped_fields=True)
    return to_crowd_cache_schema(df).to_csv(index=False)


def _old_layout_csv():
    """An hour cached before: the block's detections with lowercase names."""
    return pd.DataFrame(
        {
            "timeinstant": ["2026-11-02 09:10:00", "2026-11-02 09:20:00"],
            "entityId": [ENTITY, ENTITY],
            "israndommac": [0, 0],
            "visitorid": ["vOld1", "vOld2"],
            "detectiontype": [2, 2],
        }
    ).to_csv(index=False)


def _read(csvs, measure_ids, start, end):
    request = [
        {
            "device_ids": [ENTITY],
            "measure_ids": measure_ids,
            "options": {"start_date": start.isoformat(), "end_date": end.isoformat(),
                        "tenant": "t", "scope": "/"},
        }
    ]
    files = iter([pd.read_csv(io.StringIO(c)) for c in csvs])
    with patch.object(aether_link_helper, "_download_and_load_cache_file", side_effect=lambda *_: next(files, None)):
        return aether_link_helper.get_time_series_in_df_format(
            request, df_live_row_processing_lambda=crowd_row_processing_lambda,
            skip_aether=True, drop_nan=True,
        )


def test_written_hour_has_every_detection_in_the_fixed_layout():
    out = pd.read_csv(io.StringIO(_written_csv()))

    assert sorted(out["visitorId"]) == ["vA", "vB", "vC"]
    assert out["schemaVersion"].unique().tolist() == [2]
    assert out["fields"].notna().all()


def test_classification_reads_the_written_hour():
    df = _read([_written_csv()], ["visitorId", "visitorid", "detectionType", "random", "cfeBlock"],
               datetime(2026, 11, 2, 10), datetime(2026, 11, 2, 11))
    df = crowd_df_columns_rename(df)

    assert sorted(df["visitorid"]) == ["vA", "vB", "vC"]


def test_unique_visitors_reads_the_written_hour():
    df = _read([_written_csv()], ["visitorid", "visitorId", "cfeBlock"],
               datetime(2026, 11, 2, 10), datetime(2026, 11, 2, 11))
    df = crowd_df_columns_rename(df, municipality=False, random=False, period=False, visitor_type=False)

    assert sorted(df["visitorid"].dropna()) == ["vA", "vB", "vC"]


def test_a_window_with_old_and_new_files_reads_both():
    df = _read([_old_layout_csv(), _written_csv()],
               ["visitorId", "visitorid", "detectionType", "random", "cfeBlock"],
               datetime(2026, 11, 2, 9), datetime(2026, 11, 2, 11))
    df = crowd_df_columns_rename(df)

    assert sorted(df["visitorid"]) == ["vA", "vB", "vC", "vOld1", "vOld2"]
