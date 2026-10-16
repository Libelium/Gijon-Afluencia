"""
The Smart Spot CFE block reaches the platform as r_cfe_block, not cfeBlock: without the
datamodel mapping at provisioning time the attribute keeps its object_id. Every crowd ETL
asked only for cfeBlock, got empty series and logged "No data to work with" every hour.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

import helpers.aether_link.aether_link_helper as aether_link_helper
from helpers.crowd.crowd_utils import crowd_row_processing_lambda
from schemas.crowd_data_cache_etl_request_schema import CrowdDataCacheETLEntity, CrowdDataCacheETLRequest
from schemas.crowd_flows_municipality_request_schema import (
    CrowdFlowsMunicipalityEntity,
    CrowdFlowsMunicipalityRequest,
)
from schemas.crowd_process_visitors_request_schema import ProcessVisitorsEntity, ProcessVisitorsRequest
from etls.crowd.crowd_flows_municipality_etl.extract.crowd_flows_municipality_extract import (
    CrowdFlowsMunicipalityExtract,
)
from etls.crowd.crowd_process_visitors_etl.extract.crowd_process_visitors_extract import ProcessVisitorsExtract
from etls.data_cache.crowd_data_cache_etl.extract.crowd_data_cache_extract import CrowdDataCacheExtract

URN = "urn:ngsi-ld:CrowdFlowEvent:SPTB4238A6C0A22693891E85AAF_CFE"
START = datetime(2026, 10, 16, 7, 0)
END = datetime(2026, 10, 16, 8, 0)


def _detection(visitor_id, timeinstant, random=1):
    # Same shape as a block stored in Timescale by a production Smart Spot.
    return {
        "r_cfe_rssi": -97,
        "r_cfe_fields": [{"data": "QykTMeqfQZpCEdhPjs4AbF6F6qM=", "type": 42, "length": 22}],
        "r_cfe_random": random,
        "r_cfe_visitorId": visitor_id,
        "r_cfe_detectType": 2,
        "r_cfe_timeinstant": timeinstant,
    }


T0 = int(START.replace(tzinfo=timezone.utc).timestamp())
BLOCKS = [
    (T0 + 60, [_detection("pIlug9cf5erfZe6Aw5WQLDUzU8Y=", T0 + 59), _detection("JJHo/DNaD5iCEa6FWo4m5dzUJiQ=", T0 + 58, 2)]),
    (T0 + 900, [_detection("pIlug9cf5erfZe6Aw5WQLDUzU8Y=", T0 + 899)]),
]


def _timeseries_response(measure_id, device_ids):
    return [
        {
            "time_series": [
                {
                    "device_id": device_id,
                    "measure_id": measure_id,
                    "values": [
                        {"timestamp": datetime.fromtimestamp(ts, timezone.utc).isoformat(), "value": block}
                        for ts, block in BLOCKS
                    ],
                }
                for device_id in device_ids
            ]
        }
    ]


def _aether_serving(measure_id):
    """Fake Aether Link that, like Timescale, only returns the measure stored under that exact name."""

    def get_time_series(request):
        return [
            _timeseries_response(measure_id, r["device_ids"])[0]
            if measure_id in r["measure_ids"]
            else {"time_series": []}
            for r in request
        ]

    return get_time_series


@pytest.mark.parametrize("measure_id", ["r_cfe_block", "cfeBlock"])
def test_the_block_is_exploded_whatever_its_attribute_name(measure_id):
    df = aether_link_helper.time_series_to_df(_timeseries_response(measure_id, [URN]))

    result = crowd_row_processing_lambda(df)

    assert "r_cfe_block" not in result.columns and "cfeBlock" not in result.columns
    assert result["visitorId"].tolist() == [
        "pIlug9cf5erfZe6Aw5WQLDUzU8Y=",
        "JJHo/DNaD5iCEa6FWo4m5dzUJiQ=",
        "pIlug9cf5erfZe6Aw5WQLDUzU8Y=",
    ]
    assert result["detectionType"].tolist() == [2, 2, 2]
    assert result["random"].tolist() == [1, 2, 1]
    # The detection's own timestamp, not the one of the notification that carried the block.
    assert result["timeinstant"].iloc[0] == pd.Timestamp(T0 + 59, unit="s")


def test_rows_under_either_name_are_kept_when_both_exist():
    df = pd.DataFrame(
        {
            "timeinstant": ["2026-10-16T07:01:00Z", "2026-10-16T07:15:00Z"],
            "entityId": [URN, URN],
            "cfeBlock": [[_detection("a", T0 + 59)], None],
            "r_cfe_block": [None, [_detection("b", T0 + 899)]],
        }
    )

    result = crowd_row_processing_lambda(df)

    assert sorted(result["visitorId"]) == ["a", "b"]


EXTRACTORS = [
    (
        ProcessVisitorsExtract,
        ProcessVisitorsRequest,
        ProcessVisitorsEntity,
        "etls.crowd.crowd_process_visitors_etl.extract.crowd_process_visitors_extract",
    ),
    (
        CrowdFlowsMunicipalityExtract,
        CrowdFlowsMunicipalityRequest,
        CrowdFlowsMunicipalityEntity,
        "etls.crowd.crowd_flows_municipality_etl.extract.crowd_flows_municipality_extract",
    ),
]


@pytest.mark.parametrize("extractor_class, request_class, entity_class, module", EXTRACTORS, ids=["ProcessVisitors", "FlowsMunicipality"])
def test_live_extractors_find_visitors_stored_as_r_cfe_block(extractor_class, request_class, entity_class, module):
    request = request_class(
        entities=[entity_class(id=1, tenant="pid_gijon", scope="/", urn=URN)],
        start_date=START,
        end_date=END,
        user_id=1,
    )
    db = MagicMock()

    with patch.object(aether_link_helper, "get_time_series", side_effect=_aether_serving("r_cfe_block")), patch.object(
        aether_link_helper, "get_time_series_from_data_cache", return_value=pd.DataFrame()
    ), patch(f"{module}.get_user_crowd_visitor", return_value=[]):
        result = extractor_class(request=request, main_db=db, realtime_db=db).extract()

    assert result, "the extractor found no data"
    assert sorted(result["visitors"]) == ["JJHo/DNaD5iCEa6FWo4m5dzUJiQ=", "pIlug9cf5erfZe6Aw5WQLDUzU8Y="]


def test_data_cache_stores_and_deletes_the_r_cfe_block_series():
    request = CrowdDataCacheETLRequest(
        entities=[CrowdDataCacheETLEntity(id=1, tenant="pid_gijon", scope="/", urn=URN)],
        start_date=START,
        end_date=END,
        user_id=1,
    )
    db = MagicMock()

    with patch.object(aether_link_helper, "get_time_series", side_effect=_aether_serving("r_cfe_block")):
        result = CrowdDataCacheExtract(request=request, main_db=db, realtime_db=db).extract()

    assert result, "the data cache extractor failed"
    assert len(result["df_by_entity"][URN]) == 3
    # The same list drives the delete after upload: the raw series must be in it.
    assert "r_cfe_block" in result["variables"]
