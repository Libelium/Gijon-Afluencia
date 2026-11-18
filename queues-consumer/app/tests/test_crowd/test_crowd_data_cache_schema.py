"""
Layout of the crowd data cache CSVs for the Smart Spot firmware versions.

- Older firmware (HOP..., until sep-2026): one row per detection with loose
  attributes (visitorId, detectionType, random, rssi, ssid, signature, period).
- Newer firmware: a cfeBlock with r_cfe_* keys, one element per detection. It
  comes as a list or, with one detection, as a dict. The first builds carry
  r_cfe_ssid / r_cfe_signature; the current ones r_cfe_fields ([{type, length, data}]).

The cache must write all of them with the same columns, names and types, and
the reader used by the advanced crowd ETLs must still read the old mixed files.
"""

import json
from datetime import datetime
from unittest.mock import patch

import pandas as pd
import pytest

import helpers.aether_link.aether_link_helper as aether_link_helper
from helpers.crowd.crowd_utils import (
    CROWD_CACHE_COLUMNS,
    coalesce_legacy_crowd_columns,
    crowd_row_processing_lambda,
    to_crowd_cache_schema,
)

CACHE_RENAMES = {
    "r_cfe_random": "random",
    "r_cfe_visitorId": "visitorId",
    "r_cfe_detectType": "detectionType",
    "r_cfe_timeinstant": "timeinstant",
    "r_cfe_rssi": "rssi",
    "r_cfe_ssid": "ssid",
    "r_cfe_signature": "signature",
}

ENTITY_OLD = "urn:ngsi-ld:CrowdFlowEvent:HOP9454c54a17aa_CFE"
ENTITY_NEW = "urn:ngsi-ld:CrowdFlowEvent:SPTA808421CE3AC8859C1477653_CFE"

# 2026-11-02 10:05:00 UTC
T0 = 1793613900

FIELDS = [
    {"type": 1, "length": 1, "data": "Bg=="},
    {"type": 255, "length": 9, "data": "dmVuZG9y"},
]


def _old_firmware_row(**overrides):
    row = {
        "timeinstant": "2026-11-02T10:05:00",
        "entityId": ENTITY_OLD,
        "visitorId": "vA",
        "detectionType": 1.0,
        "random": 0.0,
        "rssi": -70.0,
        "ssid": "home",
        "signature": "sigA",
        "period": 5.0,
        "cfeBlock": None,
    }
    row.update(overrides)
    return row


def _new_firmware_row(block, timeinstant="2026-11-02T10:06:00"):
    return {"timeinstant": timeinstant, "entityId": ENTITY_NEW, "cfeBlock": block}


def _detection(offset, visitor, detect_type=2, random=2, **extra):
    return {"r_cfe_timeinstant": T0 + offset, "r_cfe_detectType": detect_type,
            "r_cfe_random": random, "r_cfe_visitorId": visitor, "r_cfe_rssi": -80, **extra}


def _cache(rows):
    df = crowd_row_processing_lambda(pd.DataFrame(rows), CACHE_RENAMES, keep_unmapped_fields=True)
    return to_crowd_cache_schema(df)


def test_old_firmware_rows_use_the_fixed_layout_with_integer_types():
    out = _cache([_old_firmware_row()])

    assert list(out.columns) == CROWD_CACHE_COLUMNS
    row = out.iloc[0]
    assert row["visitorId"] == "vA"
    assert row["detectionType"] == 1 and str(out["detectionType"].dtype) == "Int64"
    assert row["random"] == 0 and str(out["random"].dtype) == "Int64"
    assert row["rssi"] == -70 and row["period"] == 5
    assert row["timeinstant"] == "2026-11-02T10:05:00.000000"
    assert pd.isna(row["fields"])
    assert row["schemaVersion"] == 2


def test_first_new_firmware_block_keeps_rssi_ssid_and_signature():
    block = [
        _detection(0, "vB", detect_type=1, random=1, r_cfe_ssid="x", r_cfe_signature="sB"),
        _detection(10, "vC", detect_type=2, random=2),
    ]
    out = _cache([_new_firmware_row(block)])

    assert list(out.columns) == CROWD_CACHE_COLUMNS
    assert out["visitorId"].tolist() == ["vB", "vC"]
    assert out["detectionType"].tolist() == [1, 2]
    assert out["random"].tolist() == [1, 2]
    assert out["rssi"].tolist() == [-80, -80]
    assert out.loc[0, "ssid"] == "x" and out.loc[0, "signature"] == "sB"
    assert out["timeinstant"].tolist() == [
        "2026-11-02T10:05:00.000000",
        "2026-11-02T10:05:10.000000",
    ]


def test_current_new_firmware_r_cfe_fields_are_written_as_json():
    block = [
        _detection(0, "vD", r_cfe_fields=FIELDS),
        _detection(1, "vE", r_cfe_fields=[]),
    ]
    out = _cache([_new_firmware_row(block)])

    assert json.loads(out.loc[0, "fields"]) == FIELDS
    assert json.loads(out.loc[1, "fields"]) == []
    assert out["ssid"].isna().all() and out["signature"].isna().all()


def test_block_with_a_single_detection_sent_as_a_dict():
    out = _cache([_new_firmware_row(_detection(0, "vH", r_cfe_fields=FIELDS))])

    assert out["visitorId"].tolist() == ["vH"]
    assert json.loads(out.loc[0, "fields"]) == FIELDS


def test_empty_block_does_not_leave_a_row_with_only_the_entity():
    json_block = json.dumps([_detection(0, "vG", r_cfe_fields=None)])
    out = _cache([_new_firmware_row([]), _new_firmware_row(json_block)])

    assert out["visitorId"].tolist() == ["vG"]
    assert out["timeinstant"].notna().all()


def test_both_firmwares_in_the_same_hour_share_one_set_of_columns():
    rows = [
        _old_firmware_row(),
        _new_firmware_row([_detection(30, "vB")]),
        # Another attribute of the notification on its own timestamp: not a detection
        {"timeinstant": "2026-11-02T10:07:00", "entityId": ENTITY_NEW, "period": 5.0, "cfeBlock": None},
    ]
    out = _cache(rows)

    assert list(out.columns) == CROWD_CACHE_COLUMNS
    assert out["visitorId"].tolist() == ["vA", "vB"]
    assert out["random"].tolist() == [0, 2]
    assert out["detectionType"].tolist() == [1, 2]


def test_detection_without_its_own_timestamp_takes_the_notification_one():
    block = [{"r_cfe_detectType": 1, "r_cfe_random": 0, "r_cfe_visitorId": "vF"}]
    out = _cache([_new_firmware_row(block, timeinstant="2026-11-02T10:06:00.250")])

    assert out.loc[0, "timeinstant"] == "2026-11-02T10:06:00.250000"


def test_default_processing_used_by_advanced_etls_does_not_add_columns():
    """The advanced ETLs dropna() every row: no extra, often-empty columns."""
    out = crowd_row_processing_lambda(pd.DataFrame([_new_firmware_row([_detection(0, "vD", r_cfe_fields=FIELDS)])]))

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


def test_cache_reader_keeps_rows_of_old_mixed_files_and_new_files():
    """
    A batch that mixes old lowercase/camelCase files used to end up with two
    'visitorId' columns after the rename, and dropna() removed every row.
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
    new_file = _cache([_old_firmware_row(timeinstant="2026-09-04T07:30:00", visitorId="vC")])
    files = iter([old_mixed, new_file])

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
    ["2026-09-04 07:10:00", "2026-09-04T07:10:00", "2026-09-04T07:10:00.000000"],
)
def test_cache_reader_accepts_every_timeinstant_format_seen(value):
    df = aether_link_helper._normalize_timeinstant_column(pd.DataFrame({"timeinstant": [value]}))

    assert df["timeinstant"].tolist() == [pd.Timestamp("2026-09-04 07:10:00")]
    assert (df["timeinstant"] >= datetime(2026, 9, 4, 7)).all()
