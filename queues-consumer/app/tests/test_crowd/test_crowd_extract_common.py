"""
Common extraction tests for FlowsMunicipality, ProcessVisitors, and Classification Crowd ETLs.

These ETLs share the same extraction logic:
1. Fetch data via get_time_series_in_df_format with crowd_row_processing_lambda
2. Normalize columns via crowd_df_columns_rename
3. Extract unique visitors
4. Get previous visitor types from DB

This file contains parameterized tests that run against the extractors.
"""

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from datetime import datetime

# --- Schemas ---
from schemas.crowd_flows_municipality_request_schema import (
    CrowdFlowsMunicipalityRequest,
    CrowdFlowsMunicipalityEntity,
)
from schemas.crowd_process_visitors_request_schema import (
    ProcessVisitorsRequest,
    ProcessVisitorsEntity,
)
from schemas.crowd_classification_request_schema import (
    CrowdClassificationRequest,
    CrowdClassificationEntity,
)

# --- Extractors ---
from etls.crowd.crowd_flows_municipality_etl.extract.crowd_flows_municipality_extract import (
    CrowdFlowsMunicipalityExtract,
)
from etls.crowd.crowd_process_visitors_etl.extract.crowd_process_visitors_extract import (
    ProcessVisitorsExtract,
)
from etls.crowd.crowd_classification_etl.etl import CrowdClassificationETL


@pytest.fixture
def mock_main_db():
    """Provides a mock for the Platform DB session."""
    return MagicMock()


@pytest.fixture
def mock_realtime_db():
    """Provides a mock for the Realtime DB session."""
    return MagicMock()


# =======================================================================
# --- ENTITY FACTORIES ---
# =======================================================================


def _create_flows_municipality_entity(entity_id: int, urn_suffix: str, name: str = None):
    return CrowdFlowsMunicipalityEntity(
        id=entity_id,
        urn=f"urn:ngsi-ld:CrowdFlowEvent:{urn_suffix}",
        tenant="pid",
        scope="/",
        name=name,
    )


def _create_process_visitors_entity(entity_id: int, urn_suffix: str, name: str = None):
    return ProcessVisitorsEntity(
        id=entity_id,
        urn=f"urn:ngsi-ld:CrowdFlowEvent:{urn_suffix}",
        tenant="pid",
        scope="/",
        name=name,
    )


def _create_classification_entity(entity_id: int, urn_suffix: str, name: str = None):
    return CrowdClassificationEntity(
        id=entity_id,
        urn=f"urn:ngsi-ld:CrowdFlowEvent:{urn_suffix}",
        tenant="pid",
        scope="/",
        name=name,
    )


# =======================================================================
# --- TEST DATA FIXTURES ---
# =======================================================================


@pytest.fixture
def timeseries_data_camelcase():
    """
    Sample data as it comes from get_time_series_in_df_format.
    Both TimescaleDB and S3 cache data arrive in camelCase format.
    """
    return pd.DataFrame(
        {
            "timeinstant": [
                "2025-01-24T07:40:02",
                "2025-01-24T07:41:02",
                "2025-01-24T07:41:03",
                "2025-01-24T07:42:03",
            ],
            "random": [0.0, 0.0, 0.0, 1.0],
            "entityId": [
                "urn:ngsi-ld:CrowdFlowEvent:sensor-01_CFE",
                "urn:ngsi-ld:CrowdFlowEvent:sensor-01_CFE",
                "urn:ngsi-ld:CrowdFlowEvent:sensor-01_CFE",
                "urn:ngsi-ld:CrowdFlowEvent:sensor-01_CFE",
            ],
            "detectionType": [2.0, 2.0, 1.0, 2.0],
            "visitorId": [
                "visitor_001",
                "visitor_001",
                "visitor_002",
                "visitor_003",
            ],
        }
    )


@pytest.fixture
def timeseries_data_without_random():
    """Sample data without 'random' column."""
    return pd.DataFrame(
        {
            "timeinstant": [
                "2025-01-24T07:40:02",
                "2025-01-24T07:41:02",
            ],
            "entityId": [
                "urn:ngsi-ld:CrowdFlowEvent:sensor-01_CFE",
                "urn:ngsi-ld:CrowdFlowEvent:sensor-01_CFE",
            ],
            "detectionType": [2.0, 1.0],
            "visitorId": [
                "visitor_001",
                "visitor_002",
            ],
        }
    )


# =======================================================================
# --- ETL CONFIGURATIONS ---
# =======================================================================


# ETLs that return dict from extract()
ETL_CONFIGS_DICT_RETURN = [
    {
        "name": "FlowsMunicipality",
        "extractor_class": CrowdFlowsMunicipalityExtract,
        "request_class": CrowdFlowsMunicipalityRequest,
        "entity_factory": _create_flows_municipality_entity,
        "patch_path": "etls.crowd.crowd_flows_municipality_etl.extract.crowd_flows_municipality_extract",
        "request_params": lambda entities: {
            "entities": entities,
            "start_date": datetime(2023, 1, 1, 10, 0, 0),
            "end_date": datetime(2023, 1, 1, 11, 0, 0),
            "user_id": 1,
            "mode": "tourism",
        },
    },
    {
        "name": "ProcessVisitors",
        "extractor_class": ProcessVisitorsExtract,
        "request_class": ProcessVisitorsRequest,
        "entity_factory": _create_process_visitors_entity,
        "patch_path": "etls.crowd.crowd_process_visitors_etl.extract.crowd_process_visitors_extract",
        "request_params": lambda entities: {
            "entities": entities,
            "start_date": datetime(2023, 1, 1, 10, 0, 0),
            "end_date": datetime(2023, 1, 1, 11, 0, 0),
            "user_id": 1,
            "mode": "tourism",
        },
    },
]

# Classification ETL (returns bool, stores data internally)
CLASSIFICATION_CONFIG = {
    "name": "Classification",
    "extractor_class": CrowdClassificationETL,
    "request_class": CrowdClassificationRequest,
    "entity_factory": _create_classification_entity,
    "patch_path": "etls.crowd.crowd_classification_etl.etl",
    "request_params": lambda entities: {
        "entities": entities,
        "start_date": datetime(2023, 1, 1, 10, 0, 0),
        "end_date": datetime(2023, 1, 31, 11, 0, 0),
        "user_id": 1,
        "mode": "monthly",
    },
}

# All ETLs for batched request tests (request format is the same)
ALL_ETL_CONFIGS = ETL_CONFIGS_DICT_RETURN + [CLASSIFICATION_CONFIG]


# =======================================================================
# --- COMMON EXTRACTION TESTS (Dict Return ETLs) ---
# =======================================================================


class TestCrowdExtractCommon:
    """Common tests for ETLs that return dict from extract() (FlowsMunicipality, ProcessVisitors)."""

    @pytest.mark.parametrize("etl_config", ETL_CONFIGS_DICT_RETURN, ids=lambda c: c["name"])
    def test_extract_returns_dict_with_expected_keys(
        self, etl_config, timeseries_data_camelcase, mock_main_db, mock_realtime_db
    ):
        """Test that extract returns dict with df_raw, visitors, and previous_visitor_types."""
        entities = [etl_config["entity_factory"](1, "sensor-01_CFE", "Sensor Alpha")]
        request_params = etl_config["request_params"](entities)
        request = etl_config["request_class"](**request_params)

        patch_path = etl_config["patch_path"]

        with patch(
            f"{patch_path}.aether_link_helper.get_time_series_in_df_format",
            return_value=timeseries_data_camelcase,
        ), patch(
            f"{patch_path}.get_user_crowd_visitor",
            return_value=[],
        ):
            extractor = etl_config["extractor_class"](
                request=request,
                main_db=mock_main_db,
                realtime_db=mock_realtime_db,
            )

            result = extractor.extract()

            assert isinstance(result, dict), f"{etl_config['name']} should return dict"
            assert "df_raw" in result, f"{etl_config['name']} should have df_raw key"
            assert "visitors" in result, f"{etl_config['name']} should have visitors key"
            assert "previous_visitor_types" in result, f"{etl_config['name']} should have previous_visitor_types key"

    @pytest.mark.parametrize("etl_config", ETL_CONFIGS_DICT_RETURN, ids=lambda c: c["name"])
    def test_extract_previous_visitor_types_mapping(
        self, etl_config, timeseries_data_camelcase, mock_main_db, mock_realtime_db
    ):
        """Test that previous visitor types are correctly mapped from DB."""
        entities = [etl_config["entity_factory"](1, "sensor-01_CFE", "Sensor Alpha")]
        request_params = etl_config["request_params"](entities)
        request = etl_config["request_class"](**request_params)

        patch_path = etl_config["patch_path"]

        # Mock a visitor in DB
        mock_visitor = MagicMock()
        mock_visitor.visitor_id = "visitor_001"
        mock_visitor.visitor_type = "Tourist"

        with patch(
            f"{patch_path}.aether_link_helper.get_time_series_in_df_format",
            return_value=timeseries_data_camelcase,
        ), patch(
            f"{patch_path}.get_user_crowd_visitor",
            return_value=[mock_visitor],
        ):
            extractor = etl_config["extractor_class"](
                request=request,
                main_db=mock_main_db,
                realtime_db=mock_realtime_db,
            )

            result = extractor.extract()

            assert "visitor_001" in result["previous_visitor_types"]
            assert result["previous_visitor_types"]["visitor_001"] == "Tourist"

    @pytest.mark.parametrize("etl_config", ETL_CONFIGS_DICT_RETURN, ids=lambda c: c["name"])
    def test_extract_extracts_unique_visitors(
        self, etl_config, timeseries_data_camelcase, mock_main_db, mock_realtime_db
    ):
        """Test that unique visitors are correctly extracted."""
        entities = [etl_config["entity_factory"](1, "sensor-01_CFE", "Sensor Alpha")]
        request_params = etl_config["request_params"](entities)
        request = etl_config["request_class"](**request_params)

        patch_path = etl_config["patch_path"]

        with patch(
            f"{patch_path}.aether_link_helper.get_time_series_in_df_format",
            return_value=timeseries_data_camelcase,
        ), patch(
            f"{patch_path}.get_user_crowd_visitor",
            return_value=[],
        ):
            extractor = etl_config["extractor_class"](
                request=request,
                main_db=mock_main_db,
                realtime_db=mock_realtime_db,
            )

            result = extractor.extract()

            # timeseries_data_camelcase has 3 unique visitors
            assert len(result["visitors"]) == 3


# =======================================================================
# --- COLUMN NORMALIZATION TESTS ---
# =======================================================================


class TestCrowdExtractColumnNormalization:
    """Tests for column normalization in crowd ETL extractors."""

    @pytest.mark.parametrize("etl_config", ETL_CONFIGS_DICT_RETURN, ids=lambda c: c["name"])
    def test_extract_normalizes_camelcase_to_lowercase(
        self, etl_config, timeseries_data_camelcase, mock_main_db, mock_realtime_db
    ):
        """Test that camelCase columns are normalized to lowercase."""
        entities = [etl_config["entity_factory"](1, "sensor-01_CFE", "Sensor Alpha")]
        request_params = etl_config["request_params"](entities)
        request = etl_config["request_class"](**request_params)

        patch_path = etl_config["patch_path"]

        with patch(
            f"{patch_path}.aether_link_helper.get_time_series_in_df_format",
            return_value=timeseries_data_camelcase,
        ), patch(
            f"{patch_path}.get_user_crowd_visitor",
            return_value=[],
        ):
            extractor = etl_config["extractor_class"](
                request=request,
                main_db=mock_main_db,
                realtime_db=mock_realtime_db,
            )

            result = extractor.extract()
            df = result["df_raw"]

            # Check columns are normalized to lowercase
            assert "entityid" in df.columns
            assert "visitorid" in df.columns
            assert "detectiontype" in df.columns
            assert "israndommac" in df.columns

            # Check camelCase columns are renamed
            assert "entityId" not in df.columns
            assert "visitorId" not in df.columns
            assert "detectionType" not in df.columns
            assert "random" not in df.columns

    @pytest.mark.parametrize("etl_config", ETL_CONFIGS_DICT_RETURN, ids=lambda c: c["name"])
    def test_extract_adds_default_columns(
        self, etl_config, timeseries_data_camelcase, mock_main_db, mock_realtime_db
    ):
        """Test that default columns are added (municipality, period, visitortype)."""
        entities = [etl_config["entity_factory"](1, "sensor-01_CFE", "Sensor Alpha")]
        request_params = etl_config["request_params"](entities)
        request = etl_config["request_class"](**request_params)

        patch_path = etl_config["patch_path"]

        with patch(
            f"{patch_path}.aether_link_helper.get_time_series_in_df_format",
            return_value=timeseries_data_camelcase,
        ), patch(
            f"{patch_path}.get_user_crowd_visitor",
            return_value=[],
        ):
            extractor = etl_config["extractor_class"](
                request=request,
                main_db=mock_main_db,
                realtime_db=mock_realtime_db,
            )

            result = extractor.extract()
            df = result["df_raw"]

            # Check default columns are added
            assert "municipality" in df.columns
            assert df["municipality"].iloc[0] == "NA"

            assert "period" in df.columns
            assert df["period"].iloc[0] == 5

            assert "visitortype" in df.columns
            assert df["visitortype"].iloc[0] == "Resident"

    @pytest.mark.parametrize("etl_config", ETL_CONFIGS_DICT_RETURN, ids=lambda c: c["name"])
    def test_extract_handles_missing_random_column(
        self, etl_config, timeseries_data_without_random, mock_main_db, mock_realtime_db
    ):
        """Test that extract handles data without 'random' column."""
        entities = [etl_config["entity_factory"](1, "sensor-01_CFE", "Sensor Alpha")]
        request_params = etl_config["request_params"](entities)
        request = etl_config["request_class"](**request_params)

        patch_path = etl_config["patch_path"]

        with patch(
            f"{patch_path}.aether_link_helper.get_time_series_in_df_format",
            return_value=timeseries_data_without_random,
        ), patch(
            f"{patch_path}.get_user_crowd_visitor",
            return_value=[],
        ):
            extractor = etl_config["extractor_class"](
                request=request,
                main_db=mock_main_db,
                realtime_db=mock_realtime_db,
            )

            result = extractor.extract()

            assert isinstance(result, dict)
            df = result["df_raw"]

            # israndommac should exist and default to False
            assert "israndommac" in df.columns
            assert df["israndommac"].iloc[0] == False

    @pytest.mark.parametrize("etl_config", ETL_CONFIGS_DICT_RETURN, ids=lambda c: c["name"])
    def test_extract_converts_random_to_bool(
        self, etl_config, mock_main_db, mock_realtime_db
    ):
        """Test that 'random' column values are converted to boolean."""
        entities = [etl_config["entity_factory"](1, "sensor-01_CFE", "Sensor Alpha")]
        request_params = etl_config["request_params"](entities)
        request = etl_config["request_class"](**request_params)

        patch_path = etl_config["patch_path"]

        data_with_random_floats = pd.DataFrame(
            {
                "timeinstant": ["2025-01-24T07:40:02", "2025-01-24T07:41:02"],
                "entityId": ["urn:ngsi-ld:CrowdFlowEvent:sensor-01_CFE"] * 2,
                "visitorId": ["v1", "v2"],
                "detectionType": [2.0, 1.0],
                "random": [0.0, 1.0],
            }
        )

        with patch(
            f"{patch_path}.aether_link_helper.get_time_series_in_df_format",
            return_value=data_with_random_floats,
        ), patch(
            f"{patch_path}.get_user_crowd_visitor",
            return_value=[],
        ):
            extractor = etl_config["extractor_class"](
                request=request,
                main_db=mock_main_db,
                realtime_db=mock_realtime_db,
            )

            result = extractor.extract()
            df = result["df_raw"]

            # israndommac should be boolean
            assert df["israndommac"].dtype == bool
            assert df["israndommac"].iloc[0] == False
            assert df["israndommac"].iloc[1] == True


# =======================================================================
# --- EMPTY DATA HANDLING TESTS ---
# =======================================================================


class TestCrowdExtractEmptyData:
    """Tests for empty data handling in crowd ETL extractors."""

    @pytest.mark.parametrize("etl_config", ETL_CONFIGS_DICT_RETURN, ids=lambda c: c["name"])
    def test_extract_handles_empty_dataframe(
        self, etl_config, mock_main_db, mock_realtime_db
    ):
        """Test that extract handles empty DataFrame gracefully."""
        entities = [etl_config["entity_factory"](1, "sensor-01_CFE", "Sensor Alpha")]
        request_params = etl_config["request_params"](entities)
        request = etl_config["request_class"](**request_params)

        patch_path = etl_config["patch_path"]

        with patch(
            f"{patch_path}.aether_link_helper.get_time_series_in_df_format",
            return_value=pd.DataFrame(),
        ), patch(
            f"{patch_path}.get_user_crowd_visitor",
            return_value=[],
        ):
            extractor = etl_config["extractor_class"](
                request=request,
                main_db=mock_main_db,
                realtime_db=mock_realtime_db,
            )

            result = extractor.extract()

            # Should return False or dict with None/empty df_raw
            if isinstance(result, dict):
                assert result["df_raw"] is None or result["df_raw"].empty
            else:
                assert result is False


# =======================================================================
# --- BATCHED REQUEST TESTS ---
# =======================================================================


class TestCrowdExtractBatchedRequest:
    """Tests for batched timeseries request in all crowd ETL extractors (including Classification)."""

    @pytest.mark.parametrize("etl_config", ALL_ETL_CONFIGS, ids=lambda c: c["name"])
    def test_extract_batches_multiple_entities(
        self, etl_config, timeseries_data_camelcase, mock_main_db, mock_realtime_db
    ):
        """Test that multiple entities are batched into a single request."""
        entities = [
            etl_config["entity_factory"](1, "sensor-01_CFE", "Sensor Alpha"),
            etl_config["entity_factory"](2, "sensor-02_CFE", "Sensor Beta"),
        ]
        request_params = etl_config["request_params"](entities)
        request = etl_config["request_class"](**request_params)

        patch_path = etl_config["patch_path"]

        captured_request = []

        def capture_request(request_data, **kwargs):
            captured_request.append(request_data)
            return timeseries_data_camelcase

        with patch(
            f"{patch_path}.aether_link_helper.get_time_series_in_df_format",
            side_effect=capture_request,
        ), patch(
            f"{patch_path}.get_user_crowd_visitor",
            return_value=[],
        ):
            extractor = etl_config["extractor_class"](
                request=request,
                main_db=mock_main_db,
                realtime_db=mock_realtime_db,
            )

            extractor.extract()

            # Should have made exactly 1 request (batched)
            assert len(captured_request) == 1

            # The request should contain both entity URNs in device_ids
            request_data = captured_request[0]
            assert len(request_data) == 1  # Single batched request
            device_ids = request_data[0]["device_ids"]
            assert len(device_ids) == 2
            assert "urn:ngsi-ld:CrowdFlowEvent:sensor-01_CFE" in device_ids
            assert "urn:ngsi-ld:CrowdFlowEvent:sensor-02_CFE" in device_ids

    @pytest.mark.parametrize("etl_config", ALL_ETL_CONFIGS, ids=lambda c: c["name"])
    def test_extract_uses_first_entity_tenant_and_scope(
        self, etl_config, timeseries_data_camelcase, mock_main_db, mock_realtime_db
    ):
        """Test that tenant and scope are taken from the first entity."""
        entities = [
            etl_config["entity_factory"](1, "sensor-01_CFE", "Sensor Alpha"),
            etl_config["entity_factory"](2, "sensor-02_CFE", "Sensor Beta"),
        ]
        request_params = etl_config["request_params"](entities)
        request = etl_config["request_class"](**request_params)

        patch_path = etl_config["patch_path"]

        captured_request = []

        def capture_request(request_data, **kwargs):
            captured_request.append(request_data)
            return timeseries_data_camelcase

        with patch(
            f"{patch_path}.aether_link_helper.get_time_series_in_df_format",
            side_effect=capture_request,
        ), patch(
            f"{patch_path}.get_user_crowd_visitor",
            return_value=[],
        ):
            extractor = etl_config["extractor_class"](
                request=request,
                main_db=mock_main_db,
                realtime_db=mock_realtime_db,
            )

            extractor.extract()

            request_data = captured_request[0][0]
            options = request_data["options"]

            # Should use tenant and scope from first entity
            assert options["tenant"] == "pid"
            assert options["scope"] == "/"
