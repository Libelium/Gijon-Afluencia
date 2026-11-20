"""
Reading the Smart Spot detection block and the crowd data cache.

- The block (cfeBlock, or r_cfe_block when provisioning applies no datamodel
  mapping) holds one element per detection. It comes as a list or, with a
  single detection, as a dict; as a Python object or as a JSON/Python string.
- Cache files written so far name the newer firmware's columns in lowercase and
  the older firmware's in camelCase, sometimes both in one file. The reader must
  also read files that use only the camelCase layout, with extra columns.
"""

import json
from datetime import datetime
from unittest.mock import patch

import pandas as pd
import pytest

import helpers.aether_link.aether_link_helper as aether_link_helper
from helpers.crowd.crowd_utils import coalesce_legacy_crowd_columns, crowd_row_processing_lambda

ENTITY_OLD = "urn:ngsi-ld:CrowdFlowEvent:SS01_CFE"
ENTITY_NEW = "urn:ngsi-ld:CrowdFlowEvent:SPT0001_CFE"

# 2026-11-02 10:05:00 UTC
T0 = 1793613900

FIELDS = [
    {"type": 1, "length": 1, "data": "Bg=="},
    {"type": 255, "length": 9, "data": "dmVuZG9y"},
]


def _block_row(block, timeinstant="2026-11-02T10:06:00", name="cfeBlock"):
    return {"timeinstant": timeinstant, "entityId": ENTITY_NEW, name: block}


def _detection(offset, visitor, detect_type=2, random=2, **extra):
    return {"r_cfe_timeinstant": T0 + offset, "r_cfe_detectType": detect_type,
            "r_cfe_random": random, "r_cfe_visitorId": visitor, "r_cfe_rssi": -80, **extra}


@pytest.mark.parametrize("name", ["cfeBlock", "r_cfe_block"])
def test_block_with_a_single_detection_sent_as_a_dict(name):
    out = crowd_row_processing_lambda(pd.DataFrame([_block_row(_detection(0, "vH"), name=name)]))

    assert out["visitorId"].tolist() == ["vH"]
    assert out["detectionType"].tolist() == [2]
    assert out["timeinstant"].tolist() == [pd.Timestamp("2026-11-02 10:05:00")]


@pytest.mark.parametrize("encode", [json.dumps, str])
def test_block_sent_as_a_string(encode):
    block = encode([_detection(0, "vA"), _detection(10, "vB")])
    out = crowd_row_processing_lambda(pd.DataFrame([_block_row(block)]))

    assert out["visitorId"].tolist() == ["vA", "vB"]


def test_empty_block_does_not_leave_a_row_with_only_the_entity():
    rows = [_block_row([]), _block_row(json.dumps([_detection(0, "vG")]))]
    out = crowd_row_processing_lambda(pd.DataFrame(rows))

    assert out["visitorId"].tolist() == ["vG"]
    assert out["timeinstant"].notna().all()


def test_detection_without_its_own_timestamp_takes_the_notification_one():
    block = [{"r_cfe_detectType": 1, "r_cfe_random": 0, "r_cfe_visitorId": "vF"}]
    out = crowd_row_processing_lambda(pd.DataFrame([_block_row(block, timeinstant="2026-11-02T10:06:00.250")]))

    assert out["timeinstant"].tolist() == [pd.Timestamp("2026-11-02 10:06:00.250")]


def test_processing_used_by_advanced_etls_does_not_add_columns():
    """The advanced ETLs dropna() every row: no extra, often-empty columns."""
    out = crowd_row_processing_lambda(pd.DataFrame([_block_row([_detection(0, "vD", r_cfe_fields=FIELDS)])]))

    assert set(out.columns) == {"entityId", "random", "visitorId", "detectionType", "timeinstant"}


def test_coalesce_folds_lowercase_columns_onto_camelcase():
    legacy = pd.DataFrame(
        {
            "timeinstant": ["2026-09-04 07:00:00", "2026-09-04 07:00:01"],
            "entityId": [ENTITY_NEW, ENTITY_NEW],
            "detectionType": [1.0, None],
            "random": [0.0, None],
            "visitorId": ["vA", None],
            "israndommac": [None, 2.0],
            "visitorid": [None, "vB"],
            "detectiontype": [None, 2.0],
        }
    )
    out = coalesce_legacy_crowd_columns(legacy)

    assert list(out.columns) == ["timeinstant", "entityId", "detectionType", "random", "visitorId"]
    assert out["visitorId"].tolist() == ["vA", "vB"]
    assert out["random"].tolist() == [0.0, 2.0]


def test_cache_reader_keeps_rows_of_old_mixed_files_and_camelcase_files():
    """
    A batch that mixes lowercase and camelCase columns used to end up with two
    'visitorId' columns after the rename, and dropna() removed every row. A file
    with only camelCase columns, extra ones included, must be read too.
    """
    old_mixed = pd.DataFrame(
        {
            "timeinstant": ["2026-09-04 07:10:00", "2026-09-04T07:20:00"],
            "entityId": [ENTITY_OLD, ENTITY_OLD],
            "detectionType": [1.0, None],
            "random": [0.0, None],
            "visitorId": ["vA", None],
            "israndommac": [None, 1.0],
            "visitorid": [None, "vB"],
            "detectiontype": [None, 2.0],
        }
    )
    camelcase = pd.DataFrame(
        {
            "timeinstant": ["2026-09-04T07:30:00.000000"],
            "entityId": [ENTITY_OLD],
            "detectionType": [1],
            "random": [0],
            "visitorId": ["vC"],
            "rssi": [-70],
            "ssid": [None],
            "signature": [None],
            "fields": [json.dumps(FIELDS)],
            "period": [None],
            "schemaVersion": [2],
        }
    )
    files = iter([old_mixed, camelcase])

    request = [
        {
            "device_ids": [ENTITY_OLD],
            "measure_ids": ["visitorId", "visitorid", "detectionType", "random", "cfeBlock"],
            "options": {
                "start_date": datetime(2026, 9, 4, 7, 0).isoformat(),
                "end_date": datetime(2026, 9, 4, 9, 0).isoformat(),
                "tenant": "t",
                "scope": "/",
            },
        }
    ]

    with patch.object(aether_link_helper, "_download_and_load_cache_file", side_effect=lambda *_: next(files, None)):
        df = aether_link_helper.get_time_series_in_df_format(request, skip_aether=True, drop_nan=True)

    assert list(df.columns).count("visitorId") == 1
    assert sorted(df["visitorId"].tolist()) == ["vA", "vB", "vC"]


@pytest.mark.parametrize(
    "value",
    [
        "2026-09-04 07:10:00",
        "2026-09-04T07:10:00",
        "2026-09-04T07:10:00.000000",
        "2026-09-04T07:10:00+00:00",
        "2026-09-04T07:10:00Z",
        "2026-09-04T09:10:00.000000+02:00",
    ],
)
def test_cache_reader_accepts_every_timeinstant_format(value):
    df = aether_link_helper._normalize_timeinstant_column(pd.DataFrame({"timeinstant": [value]}))

    assert df["timeinstant"].tolist() == [pd.Timestamp("2026-09-04 07:10:00")]
    assert (df["timeinstant"] >= datetime(2026, 9, 4, 7)).all()
