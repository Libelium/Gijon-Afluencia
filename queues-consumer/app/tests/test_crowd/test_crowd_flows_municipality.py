import pytest
import pandas as pd
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timedelta

# --- Schemas ---
from schemas.crowd_flows_municipality_request_schema import (
    AllCrowdFlowsMunicipalityRequest,
    CrowdFlowsMunicipalityRequest,
    CrowdFlowsMunicipalityEntity,
)

# --- Classes Under Test ---
from etls.crowd.crowd_flows_municipality_etl.transform.crowd_flows_municipality_transform import (
    CrowdFlowsMunicipalityTransform,
)
from etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load import (
    CrowdFlowsMunicipalityLoad,
)
from jobs.crowd.all_crowd_flows_municipality_jobs import CrowdFlowsMunicipalityAll


@pytest.fixture
def mock_main_db():
    """Provides a mock for the Platform DB session."""
    return MagicMock()


@pytest.fixture
def mock_realtime_db():
    """Provides a mock for the Realtime DB session."""
    return MagicMock()


# =======================================================================
# --- HELPER FUNCTIONS ---
# =======================================================================


def _create_entity(entity_id: int, urn_suffix: str, name: str = None):
    """Factory function to create CrowdFlowsMunicipalityEntity."""
    return CrowdFlowsMunicipalityEntity(
        id=entity_id,
        urn=f"urn:ngsi-ld:CrowdFlowEvent:{urn_suffix}",
        tenant="pid",
        scope="/",
        name=name,
    )


def _get_datetime_from_request(request_obj, attr_name="end_date"):
    """Helper to extract datetime from request, handling both datetime and ISO string."""
    value = getattr(request_obj, attr_name)
    return value if isinstance(value, datetime) else datetime.fromisoformat(value)


# =======================================================================
# --- FIXTURES ---
# =======================================================================


@pytest.fixture
def sample_entities():
    """Provides sample entity data."""
    return [
        _create_entity(1, "sensor-01", "Sensor Alpha"),
        _create_entity(2, "sensor-02", "Sensor Beta"),
    ]


@pytest.fixture
def sample_entities_no_names():
    """Provides sample entity data without names."""
    return [
        _create_entity(1, "sensor-01"),
        _create_entity(2, "sensor-02"),
    ]


@pytest.fixture
def base_request_params(sample_entities):
    """Provides base parameters for creating a request."""
    return {
        "entities": sample_entities,
        "start_date": datetime(2023, 1, 1, 10, 0, 0),
        "end_date": datetime(2023, 1, 1, 11, 0, 0),
        "user_id": 1,
        "mode": "tourism",
    }


@pytest.fixture
def sample_raw_data():
    """Provides sample raw DataFrame for transform testing."""
    return pd.DataFrame(
        {
            "entityid": [
                "urn:ngsi-ld:CrowdFlowEvent:sensor-01",
                "urn:ngsi-ld:CrowdFlowEvent:sensor-02",
                "urn:ngsi-ld:CrowdFlowEvent:sensor-01",
                "urn:ngsi-ld:CrowdFlowEvent:sensor-02",
                "urn:ngsi-ld:CrowdFlowEvent:sensor-01",
            ],
            "visitorid": ["v1", "v1", "v2", "v2", "v1"],
            "timeinstant": [
                datetime(2023, 1, 1, 10, 0),
                datetime(2023, 1, 1, 10, 15),
                datetime(2023, 1, 1, 10, 5),
                datetime(2023, 1, 1, 10, 20),
                datetime(2023, 1, 1, 10, 30),
            ],
        }
    )


@pytest.fixture
def sample_transform_output():
    """Provides sample transform output for load testing."""
    return {
        "result": pd.DataFrame(
            {
                "origin_entityid": ["urn:ngsi-ld:CrowdFlowEvent:sensor-01"],
                "entityid": ["urn:ngsi-ld:CrowdFlowEvent:sensor-02"],
                "count": [2],
                "averagetransitduration": [timedelta(minutes=15)],
                "minimumtransitduration": [timedelta(minutes=10)],
                "maximumtransitduration": [timedelta(minutes=20)],
                "touristaveragetransitduration": [timedelta(minutes=15)],
                "touristminimumtransitduration": [timedelta(minutes=15)],
                "touristmaximumtransitduration": [timedelta(minutes=15)],
                "touristcount": [1],
                "residentaveragetransitduration": [timedelta(minutes=15)],
                "residentminimumtransitduration": [timedelta(minutes=15)],
                "residentmaximumtransitduration": [timedelta(minutes=15)],
                "residentcount": [1],
                "shorttermvisitoraveragetransitduration": [None],
                "shorttermvisitorminimumtransitduration": [None],
                "shorttermvisitormaximumtransitduration": [None],
                "shorttermvisitorcount": [0],
            }
        )
    }


@pytest.fixture
def timeseries_data_camelcase():
    """
    Sample data as it comes from get_time_series_in_df_format.

    Both TimescaleDB (live) and S3 cache data arrive in camelCase format:
    - TimescaleDB: processed by crowd_row_processing_lambda -> camelCase
    - S3 Cache: renamed in get_time_series_from_data_cache -> camelCase

    This is the format that crowd_df_columns_rename receives.
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
                "urn:ngsi-ld:CrowdFlowEvent:HOP9454c549c5fe_CFE",
                "urn:ngsi-ld:CrowdFlowEvent:HOP9454c549c5fe_CFE",
                "urn:ngsi-ld:CrowdFlowEvent:HOP9454c549c5fe_CFE",
                "urn:ngsi-ld:CrowdFlowEvent:HOP9454c549c5fe_CFE",
            ],
            "detectionType": [2.0, 2.0, 1.0, 2.0],
            "visitorId": [
                "4058078681d489017524688c6f111fa0bd0d288f",
                "4058078681d489017524688c6f111fa0bd0d288f",
                "0bf0ae029a5ebafcbf7dabe36785bbb0c6ea8895",
                "aa4c22906b0f6c5cd3c5992e590328dfbb94e187",
            ],
        }
    )


@pytest.fixture
def timeseries_data_without_random():
    """
    Sample data without 'random' column.
    This can happen when the column is not present in the source data.
    crowd_df_columns_rename should add it with default value False.
    """
    return pd.DataFrame(
        {
            "timeinstant": [
                "2025-01-24T07:40:02",
                "2025-01-24T07:41:02",
            ],
            "entityId": [
                "urn:ngsi-ld:CrowdFlowEvent:sensor-01",
                "urn:ngsi-ld:CrowdFlowEvent:sensor-01",
            ],
            "detectionType": [2.0, 1.0],
            "visitorId": [
                "visitor1",
                "visitor2",
            ],
        }
    )


# =======================================================================
# --- TRANSFORM TESTS ---
# =======================================================================


class TestCrowdFlowsMunicipalityTransform:
    """Test suite for the CrowdFlowsMunicipalityTransform class."""

    def test_transform_calculates_visitor_flows(
        self, base_request_params, mock_main_db, mock_realtime_db
    ):
        """Test that transform correctly calculates visitor flow transitions."""
        request = CrowdFlowsMunicipalityRequest(**base_request_params)

        # Visitor v1 moves from sensor-01 to sensor-02
        raw_data = pd.DataFrame(
            {
                "entityid": [
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-01",
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-02",
                ],
                "visitorid": ["v1", "v1"],
                "timeinstant": [
                    datetime(2023, 1, 1, 10, 0),
                    datetime(2023, 1, 1, 10, 15),
                ],
            }
        )

        extract_output = {
            "df_raw": raw_data,
            "visitors": ["v1"],
            "previous_visitor_types": {"v1": "Resident"},
        }

        transformer = CrowdFlowsMunicipalityTransform(
            request=request,
            extract_output=extract_output,
            main_db=mock_main_db,
            realtime_db=mock_realtime_db,
        )

        result = transformer.transform()

        assert isinstance(result, dict)
        assert "result" in result
        assert not result["result"].empty

    def test_transform_classifies_visitors_from_previous_types(
        self, base_request_params, mock_main_db, mock_realtime_db
    ):
        """Test that visitors are classified using previous_visitor_types."""
        request = CrowdFlowsMunicipalityRequest(**base_request_params)

        raw_data = pd.DataFrame(
            {
                "entityid": [
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-01",
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-02",
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-01",
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-02",
                ],
                "visitorid": ["v1", "v1", "v2", "v2"],
                "timeinstant": [
                    datetime(2023, 1, 1, 10, 0),
                    datetime(2023, 1, 1, 10, 15),
                    datetime(2023, 1, 1, 10, 5),
                    datetime(2023, 1, 1, 10, 20),
                ],
            }
        )

        extract_output = {
            "df_raw": raw_data,
            "visitors": ["v1", "v2"],
            "previous_visitor_types": {
                "v1": "Tourist",
                "v2": "Resident",
            },
        }

        transformer = CrowdFlowsMunicipalityTransform(
            request=request,
            extract_output=extract_output,
            main_db=mock_main_db,
            realtime_db=mock_realtime_db,
        )

        result = transformer.transform()
        result_df = result["result"]

        # Should have tourist and resident counts
        assert "touristcount" in result_df.columns
        assert "residentcount" in result_df.columns

    def test_transform_unknown_visitors_classified_as_short_term(
        self, base_request_params, mock_main_db, mock_realtime_db
    ):
        """Test that unknown visitors are classified as ShortTermVisitor."""
        request = CrowdFlowsMunicipalityRequest(**base_request_params)

        raw_data = pd.DataFrame(
            {
                "entityid": [
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-01",
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-02",
                ],
                "visitorid": ["unknown_visitor", "unknown_visitor"],
                "timeinstant": [
                    datetime(2023, 1, 1, 10, 0),
                    datetime(2023, 1, 1, 10, 15),
                ],
            }
        )

        extract_output = {
            "df_raw": raw_data,
            "visitors": ["unknown_visitor"],
            "previous_visitor_types": {},  # Empty - visitor not in database
        }

        transformer = CrowdFlowsMunicipalityTransform(
            request=request,
            extract_output=extract_output,
            main_db=mock_main_db,
            realtime_db=mock_realtime_db,
        )

        result = transformer.transform()
        result_df = result["result"]

        # ShortTermVisitor count should be present
        assert "shorttermvisitorcount" in result_df.columns

    def test_transform_calculates_transit_duration_statistics(
        self, base_request_params, mock_main_db, mock_realtime_db
    ):
        """Test that transform calculates avg, min, max transit durations."""
        request = CrowdFlowsMunicipalityRequest(**base_request_params)

        # Multiple visitors with different transit times
        raw_data = pd.DataFrame(
            {
                "entityid": [
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-01",
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-02",
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-01",
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-02",
                ],
                "visitorid": ["v1", "v1", "v2", "v2"],
                "timeinstant": [
                    datetime(2023, 1, 1, 10, 0),
                    datetime(2023, 1, 1, 10, 10),  # 10 min transit
                    datetime(2023, 1, 1, 10, 5),
                    datetime(2023, 1, 1, 10, 25),  # 20 min transit
                ],
            }
        )

        extract_output = {
            "df_raw": raw_data,
            "visitors": ["v1", "v2"],
            "previous_visitor_types": {"v1": "Tourist", "v2": "Tourist"},
        }

        transformer = CrowdFlowsMunicipalityTransform(
            request=request,
            extract_output=extract_output,
            main_db=mock_main_db,
            realtime_db=mock_realtime_db,
        )

        result = transformer.transform()
        result_df = result["result"]

        # Should have duration statistics
        assert "averagetransitduration" in result_df.columns
        assert "minimumtransitduration" in result_df.columns
        assert "maximumtransitduration" in result_df.columns

    def test_transform_filters_same_origin_destination(
        self, base_request_params, mock_main_db, mock_realtime_db
    ):
        """Test that flows with same origin and destination are handled."""
        request = CrowdFlowsMunicipalityRequest(**base_request_params)

        # Visitor stays at same sensor (no actual flow)
        raw_data = pd.DataFrame(
            {
                "entityid": [
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-01",
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-01",
                ],
                "visitorid": ["v1", "v1"],
                "timeinstant": [
                    datetime(2023, 1, 1, 10, 0),
                    datetime(2023, 1, 1, 10, 15),
                ],
            }
        )

        extract_output = {
            "df_raw": raw_data,
            "visitors": ["v1"],
            "previous_visitor_types": {"v1": "Resident"},
        }

        transformer = CrowdFlowsMunicipalityTransform(
            request=request,
            extract_output=extract_output,
            main_db=mock_main_db,
            realtime_db=mock_realtime_db,
        )

        result = transformer.transform()

        # Should handle this case without error
        assert isinstance(result, dict)
        assert "result" in result

    def test_transform_aggregates_by_origin_entity(
        self, base_request_params, mock_main_db, mock_realtime_db
    ):
        """
        Test that __aggregate_by_origin_entity creates aggregated rows.

        The transform should create additional rows that aggregate statistics
        for each entity (considering both as origin and destination).
        """
        request = CrowdFlowsMunicipalityRequest(**base_request_params)

        # Two visitors with flows between two sensors
        raw_data = pd.DataFrame(
            {
                "entityid": [
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-01",
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-02",
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-01",
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-02",
                ],
                "visitorid": ["v1", "v1", "v2", "v2"],
                "timeinstant": [
                    datetime(2023, 1, 1, 10, 0),
                    datetime(2023, 1, 1, 10, 15),
                    datetime(2023, 1, 1, 10, 5),
                    datetime(2023, 1, 1, 10, 25),
                ],
            }
        )

        extract_output = {
            "df_raw": raw_data,
            "visitors": ["v1", "v2"],
            "previous_visitor_types": {"v1": "Resident", "v2": "Resident"},
        }

        transformer = CrowdFlowsMunicipalityTransform(
            request=request,
            extract_output=extract_output,
            main_db=mock_main_db,
            realtime_db=mock_realtime_db,
        )

        result = transformer.transform()
        result_df = result["result"]

        # Should have the original flow row plus aggregated rows
        # Check that aggregated rows exist (where origin_entityid == entityid)
        aggregated_rows = result_df[result_df["origin_entityid"] == result_df["entityid"]]
        assert len(aggregated_rows) > 0, "Should have aggregated rows"

    def test_transform_calculates_correct_transit_duration_values(
        self, base_request_params, mock_main_db, mock_realtime_db
    ):
        """
        Test that transit duration values are calculated correctly.

        v1: sensor-01 (10:00) -> sensor-02 (10:10) = 10 min
        v2: sensor-01 (10:05) -> sensor-02 (10:25) = 20 min

        Expected:
        - average: 15 min
        - min: 10 min
        - max: 20 min
        - count: 2
        """
        request = CrowdFlowsMunicipalityRequest(**base_request_params)

        raw_data = pd.DataFrame(
            {
                "entityid": [
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-01",
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-02",
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-01",
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-02",
                ],
                "visitorid": ["v1", "v1", "v2", "v2"],
                "timeinstant": [
                    datetime(2023, 1, 1, 10, 0),
                    datetime(2023, 1, 1, 10, 10),  # 10 min transit
                    datetime(2023, 1, 1, 10, 5),
                    datetime(2023, 1, 1, 10, 25),  # 20 min transit
                ],
            }
        )

        extract_output = {
            "df_raw": raw_data,
            "visitors": ["v1", "v2"],
            "previous_visitor_types": {"v1": "Resident", "v2": "Resident"},
        }

        transformer = CrowdFlowsMunicipalityTransform(
            request=request,
            extract_output=extract_output,
            main_db=mock_main_db,
            realtime_db=mock_realtime_db,
        )

        result = transformer.transform()
        result_df = result["result"]

        # Get the flow row (sensor-01 -> sensor-02)
        flow_row = result_df[
            (result_df["origin_entityid"] == "urn:ngsi-ld:CrowdFlowEvent:sensor-01") &
            (result_df["entityid"] == "urn:ngsi-ld:CrowdFlowEvent:sensor-02")
        ].iloc[0]

        # Verify calculated values
        assert flow_row["count"] == 2
        assert flow_row["averagetransitduration"] == timedelta(minutes=15)
        assert flow_row["minimumtransitduration"] == timedelta(minutes=10)
        assert flow_row["maximumtransitduration"] == timedelta(minutes=20)

    def test_transform_calculates_duration_by_visitor_type(
        self, base_request_params, mock_main_db, mock_realtime_db
    ):
        """
        Test that transit durations are calculated separately for each visitor type.

        v1 (Tourist): sensor-01 -> sensor-02 = 10 min
        v2 (Resident): sensor-01 -> sensor-02 = 20 min
        """
        request = CrowdFlowsMunicipalityRequest(**base_request_params)

        raw_data = pd.DataFrame(
            {
                "entityid": [
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-01",
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-02",
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-01",
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-02",
                ],
                "visitorid": ["v1", "v1", "v2", "v2"],
                "timeinstant": [
                    datetime(2023, 1, 1, 10, 0),
                    datetime(2023, 1, 1, 10, 10),  # Tourist: 10 min
                    datetime(2023, 1, 1, 10, 5),
                    datetime(2023, 1, 1, 10, 25),  # Resident: 20 min
                ],
            }
        )

        extract_output = {
            "df_raw": raw_data,
            "visitors": ["v1", "v2"],
            "previous_visitor_types": {"v1": "Tourist", "v2": "Resident"},
        }

        transformer = CrowdFlowsMunicipalityTransform(
            request=request,
            extract_output=extract_output,
            main_db=mock_main_db,
            realtime_db=mock_realtime_db,
        )

        result = transformer.transform()
        result_df = result["result"]

        # Get the flow row
        flow_row = result_df[
            (result_df["origin_entityid"] == "urn:ngsi-ld:CrowdFlowEvent:sensor-01") &
            (result_df["entityid"] == "urn:ngsi-ld:CrowdFlowEvent:sensor-02")
        ].iloc[0]

        # Tourist stats
        assert flow_row["touristcount"] == 1
        assert flow_row["touristaveragetransitduration"] == timedelta(minutes=10)

        # Resident stats
        assert flow_row["residentcount"] == 1
        assert flow_row["residentaveragetransitduration"] == timedelta(minutes=20)

        # ShortTermVisitor should be 0 or NaN
        assert flow_row["shorttermvisitorcount"] == 0 or pd.isna(flow_row["shorttermvisitorcount"])


# =======================================================================
# --- LOAD TESTS ---
# =======================================================================


class TestCrowdFlowsMunicipalityLoad:
    """Test suite for the CrowdFlowsMunicipalityLoad class."""

    def test_load_converts_timedelta_to_seconds(
        self, base_request_params, mock_main_db, mock_realtime_db
    ):
        """Test that timedelta values are converted to seconds in payload."""
        request = CrowdFlowsMunicipalityRequest(**base_request_params)

        transform_output = {
            "result": pd.DataFrame(
                {
                    "origin_entityid": ["urn:ngsi-ld:CrowdFlowEvent:sensor-01"],
                    "entityid": ["urn:ngsi-ld:CrowdFlowEvent:sensor-02"],
                    "count": [5],
                    "averagetransitduration": [timedelta(minutes=15)],
                    "minimumtransitduration": [timedelta(minutes=5)],
                    "maximumtransitduration": [timedelta(minutes=30)],
                    "touristaveragetransitduration": [timedelta(minutes=15)],
                    "touristminimumtransitduration": [timedelta(minutes=5)],
                    "touristmaximumtransitduration": [timedelta(minutes=30)],
                    "touristcount": [3],
                    "residentaveragetransitduration": [timedelta(minutes=10)],
                    "residentminimumtransitduration": [timedelta(minutes=5)],
                    "residentmaximumtransitduration": [timedelta(minutes=15)],
                    "residentcount": [2],
                    "shorttermvisitoraveragetransitduration": [None],
                    "shorttermvisitorminimumtransitduration": [None],
                    "shorttermvisitormaximumtransitduration": [None],
                    "shorttermvisitorcount": [0],
                }
            )
        }

        with patch(
            "etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load.iota_helper.publish_data"
        ) as mock_publish, patch(
            "etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load.crud_entity.get_many_by_urn",
            return_value=[],
        ), patch(
            "etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load.crud_preferences.get_user_preference",
            return_value=1,
        ), patch(
            "etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load.crud_tenant_scope.get_tenant_scope",
            return_value=("pid", "/"),
        ), patch(
            "etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load.aether_link_helper.get_iota_services",
            return_value=[{"apikey": "test-key", "resource": "/"}],
        ):
            loader = CrowdFlowsMunicipalityLoad(
                request=request,
                transform_output=transform_output,
                main_db=mock_main_db,
                realtime_db=mock_realtime_db,
            )
            loader.load()

            mock_publish.assert_called_once()
            call_args = mock_publish.call_args[1]
            payload = call_args.get("body")

            # 15 minutes = 900 seconds
            assert payload.get("averageTransitDuration") == 900
            # 5 minutes = 300 seconds
            assert payload.get("minimumTransitDuration") == 300
            # 30 minutes = 1800 seconds
            assert payload.get("maximumTransitDuration") == 1800

    def test_load_generates_entity_id_from_origin_destination(
        self, base_request_params, mock_main_db, mock_realtime_db
    ):
        """Test that entity ID is generated from origin:destination."""
        request = CrowdFlowsMunicipalityRequest(**base_request_params)

        transform_output = {
            "result": pd.DataFrame(
                {
                    "origin_entityid": ["urn:ngsi-ld:CrowdFlowEvent:sensor-01"],
                    "entityid": ["urn:ngsi-ld:CrowdFlowEvent:sensor-02"],
                    "count": [5],
                    "averagetransitduration": [timedelta(minutes=15)],
                    "minimumtransitduration": [timedelta(minutes=5)],
                    "maximumtransitduration": [timedelta(minutes=30)],
                    "touristaveragetransitduration": [timedelta(minutes=15)],
                    "touristminimumtransitduration": [timedelta(minutes=5)],
                    "touristmaximumtransitduration": [timedelta(minutes=30)],
                    "touristcount": [3],
                    "residentaveragetransitduration": [timedelta(minutes=10)],
                    "residentminimumtransitduration": [timedelta(minutes=5)],
                    "residentmaximumtransitduration": [timedelta(minutes=15)],
                    "residentcount": [2],
                    "shorttermvisitoraveragetransitduration": [None],
                    "shorttermvisitorminimumtransitduration": [None],
                    "shorttermvisitormaximumtransitduration": [None],
                    "shorttermvisitorcount": [0],
                }
            )
        }

        with patch(
            "etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load.iota_helper.publish_data"
        ) as mock_publish, patch(
            "etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load.crud_entity.get_many_by_urn",
            return_value=[],
        ), patch(
            "etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load.crud_preferences.get_user_preference",
            return_value=1,
        ), patch(
            "etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load.crud_tenant_scope.get_tenant_scope",
            return_value=("pid", "/"),
        ), patch(
            "etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load.aether_link_helper.get_iota_services",
            return_value=[{"apikey": "test-key", "resource": "/"}],
        ):
            loader = CrowdFlowsMunicipalityLoad(
                request=request,
                transform_output=transform_output,
                main_db=mock_main_db,
                realtime_db=mock_realtime_db,
            )
            loader.load()

            mock_publish.assert_called_once()
            call_args = mock_publish.call_args[1]
            entity_id = call_args.get("id")

            assert entity_id == "sensor-01:sensor-02"

    def test_load_preserves_name_for_existing_entity(
        self, base_request_params, mock_main_db, mock_realtime_db
    ):
        """Test that name is not included for existing entities."""
        request = CrowdFlowsMunicipalityRequest(**base_request_params)

        transform_output = {
            "result": pd.DataFrame(
                {
                    "origin_entityid": ["urn:ngsi-ld:CrowdFlowEvent:sensor-01"],
                    "entityid": ["urn:ngsi-ld:CrowdFlowEvent:sensor-02"],
                    "count": [50],
                    "averageTransitDuration": [timedelta(minutes=15)],
                    "minimumTransitDuration": [timedelta(minutes=5)],
                    "maximumTransitDuration": [timedelta(minutes=30)],
                    "touristAverageTransitDuration": [timedelta(minutes=15)],
                    "touristMinimumTransitDuration": [timedelta(minutes=5)],
                    "touristMaximumTransitDuration": [timedelta(minutes=30)],
                    "touristCount": [25],
                    "residentAverageTransitDuration": [timedelta(minutes=15)],
                    "residentMinimumTransitDuration": [timedelta(minutes=5)],
                    "residentMaximumTransitDuration": [timedelta(minutes=30)],
                    "residentCount": [25],
                    "shortTermVisitorAverageTransitDuration": [timedelta(minutes=15)],
                    "shortTermVisitorMinimumTransitDuration": [timedelta(minutes=5)],
                    "shortTermVisitorMaximumTransitDuration": [timedelta(minutes=30)],
                    "shortTermVisitorCount": [0],
                }
            )
        }

        mock_existing_flow = MagicMock()
        mock_existing_flow.urn = "urn:ngsi-ld:CrowdFlowEventETL:sensor-01:sensor-02"

        with patch(
            "etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load.iota_helper.publish_data"
        ) as mock_publish, patch(
            "etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load.crud_entity.get_many_by_urn",
            return_value=[mock_existing_flow],
        ), patch(
            "etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load.crud_preferences.get_user_preference",
            return_value=1,
        ), patch(
            "etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load.crud_tenant_scope.get_tenant_scope",
            return_value=("pid", "/"),
        ), patch(
            "etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load.aether_link_helper.get_iota_services",
            return_value=[{"apikey": "test-key", "resource": "/"}],
        ):
            loader = CrowdFlowsMunicipalityLoad(
                request=request,
                transform_output=transform_output,
                main_db=mock_main_db,
                realtime_db=mock_realtime_db,
            )
            loader.load()

            mock_publish.assert_called_once()
            call_args = mock_publish.call_args[1]
            payload = call_args.get("body")
            entity_id = call_args.get("id")

            assert "name" not in payload
            assert entity_id == "sensor-01:sensor-02"
            assert payload.get("count") == 50
            assert payload.get("touristCount") == 25
            assert payload.get("residentCount") == 25
            assert payload.get("averageTransitDuration") == 900

    def test_load_creates_name_for_new_entity(
        self, base_request_params, mock_main_db, mock_realtime_db
    ):
        """Test that name is generated for new entities using sensor names."""
        request = CrowdFlowsMunicipalityRequest(**base_request_params)

        transform_output = {
            "result": pd.DataFrame(
                {
                    "origin_entityid": ["urn:ngsi-ld:CrowdFlowEvent:sensor-01"],
                    "entityid": ["urn:ngsi-ld:CrowdFlowEvent:sensor-02"],
                    "count": [50],
                    "averageTransitDuration": [timedelta(minutes=15)],
                    "minimumTransitDuration": [timedelta(minutes=5)],
                    "maximumTransitDuration": [timedelta(minutes=30)],
                    "touristAverageTransitDuration": [timedelta(minutes=15)],
                    "touristMinimumTransitDuration": [timedelta(minutes=5)],
                    "touristMaximumTransitDuration": [timedelta(minutes=30)],
                    "touristCount": [25],
                    "residentAverageTransitDuration": [timedelta(minutes=15)],
                    "residentMinimumTransitDuration": [timedelta(minutes=5)],
                    "residentMaximumTransitDuration": [timedelta(minutes=30)],
                    "residentCount": [25],
                    "shortTermVisitorAverageTransitDuration": [timedelta(minutes=15)],
                    "shortTermVisitorMinimumTransitDuration": [timedelta(minutes=5)],
                    "shortTermVisitorMaximumTransitDuration": [timedelta(minutes=30)],
                    "shortTermVisitorCount": [0],
                }
            )
        }

        with patch(
            "etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load.iota_helper.publish_data"
        ) as mock_publish, patch(
            "etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load.crud_entity.get_many_by_urn",
            return_value=[],
        ), patch(
            "etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load.crud_preferences.get_user_preference",
            return_value=1,
        ), patch(
            "etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load.crud_tenant_scope.get_tenant_scope",
            return_value=("pid", "/"),
        ), patch(
            "etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load.aether_link_helper.get_iota_services",
            return_value=[{"apikey": "test-key", "resource": "/"}],
        ):
            loader = CrowdFlowsMunicipalityLoad(
                request=request,
                transform_output=transform_output,
                main_db=mock_main_db,
                realtime_db=mock_realtime_db,
            )
            loader.load()

            mock_publish.assert_called_once()
            payload = mock_publish.call_args[1].get("body")

            assert "name" in payload
            assert payload.get("name") == "From Sensor Alpha to Sensor Beta"

    def test_load_creates_fallback_name_when_no_sensor_names(
        self, base_request_params, sample_entities_no_names, mock_main_db, mock_realtime_db
    ):
        """Test that fallback name uses entity IDs when sensor names not available."""
        base_request_params["entities"] = sample_entities_no_names
        request = CrowdFlowsMunicipalityRequest(**base_request_params)

        transform_output = {
            "result": pd.DataFrame(
                {
                    "origin_entityid": ["urn:ngsi-ld:CrowdFlowEvent:sensor-01"],
                    "entityid": ["urn:ngsi-ld:CrowdFlowEvent:sensor-02"],
                    "count": [50],
                    "averageTransitDuration": [timedelta(minutes=15)],
                    "minimumTransitDuration": [timedelta(minutes=5)],
                    "maximumTransitDuration": [timedelta(minutes=30)],
                    "touristAverageTransitDuration": [timedelta(minutes=15)],
                    "touristMinimumTransitDuration": [timedelta(minutes=5)],
                    "touristMaximumTransitDuration": [timedelta(minutes=30)],
                    "touristCount": [25],
                    "residentAverageTransitDuration": [timedelta(minutes=15)],
                    "residentMinimumTransitDuration": [timedelta(minutes=5)],
                    "residentMaximumTransitDuration": [timedelta(minutes=30)],
                    "residentCount": [25],
                    "shortTermVisitorAverageTransitDuration": [timedelta(minutes=15)],
                    "shortTermVisitorMinimumTransitDuration": [timedelta(minutes=5)],
                    "shortTermVisitorMaximumTransitDuration": [timedelta(minutes=30)],
                    "shortTermVisitorCount": [0],
                }
            )
        }

        with patch(
            "etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load.iota_helper.publish_data"
        ) as mock_publish, patch(
            "etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load.crud_entity.get_many_by_urn",
            return_value=[],
        ), patch(
            "etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load.crud_preferences.get_user_preference",
            return_value=1,
        ), patch(
            "etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load.crud_tenant_scope.get_tenant_scope",
            return_value=("pid", "/"),
        ), patch(
            "etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load.aether_link_helper.get_iota_services",
            return_value=[{"apikey": "test-key", "resource": "/"}],
        ):
            loader = CrowdFlowsMunicipalityLoad(
                request=request,
                transform_output=transform_output,
                main_db=mock_main_db,
                realtime_db=mock_realtime_db,
            )
            loader.load()

            mock_publish.assert_called_once()
            payload = mock_publish.call_args[1].get("body")

            assert "name" in payload
            assert payload.get("name") == "From sensor-01 to sensor-02"

    def test_load_includes_classification_fields(
        self, base_request_params, mock_main_db, mock_realtime_db
    ):
        """Test that classification-specific fields are included in payload."""
        request = CrowdFlowsMunicipalityRequest(**base_request_params)

        transform_output = {
            "result": pd.DataFrame(
                {
                    "origin_entityid": ["urn:ngsi-ld:CrowdFlowEvent:sensor-01"],
                    "entityid": ["urn:ngsi-ld:CrowdFlowEvent:sensor-02"],
                    "count": [10],
                    "averagetransitduration": [timedelta(minutes=15)],
                    "minimumtransitduration": [timedelta(minutes=5)],
                    "maximumtransitduration": [timedelta(minutes=30)],
                    "touristaveragetransitduration": [timedelta(minutes=20)],
                    "touristminimumtransitduration": [timedelta(minutes=10)],
                    "touristmaximumtransitduration": [timedelta(minutes=30)],
                    "touristcount": [5],
                    "residentaveragetransitduration": [timedelta(minutes=10)],
                    "residentminimumtransitduration": [timedelta(minutes=5)],
                    "residentmaximumtransitduration": [timedelta(minutes=15)],
                    "residentcount": [4],
                    "shorttermvisitoraveragetransitduration": [timedelta(minutes=5)],
                    "shorttermvisitorminimumtransitduration": [timedelta(minutes=5)],
                    "shorttermvisitormaximumtransitduration": [timedelta(minutes=5)],
                    "shorttermvisitorcount": [1],
                }
            )
        }

        with patch(
            "etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load.iota_helper.publish_data"
        ) as mock_publish, patch(
            "etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load.crud_entity.get_many_by_urn",
            return_value=[],
        ), patch(
            "etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load.crud_preferences.get_user_preference",
            return_value=1,
        ), patch(
            "etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load.crud_tenant_scope.get_tenant_scope",
            return_value=("pid", "/"),
        ), patch(
            "etls.crowd.crowd_flows_municipality_etl.load.crowd_flows_municipality_load.aether_link_helper.get_iota_services",
            return_value=[{"apikey": "test-key", "resource": "/"}],
        ):
            loader = CrowdFlowsMunicipalityLoad(
                request=request,
                transform_output=transform_output,
                main_db=mock_main_db,
                realtime_db=mock_realtime_db,
            )
            loader.load()

            mock_publish.assert_called_once()
            payload = mock_publish.call_args[1].get("body")

            # Tourist fields
            assert payload.get("touristCount") == 5
            assert payload.get("touristAverageTransitDuration") == 1200  # 20 min

            # Resident fields
            assert payload.get("residentCount") == 4
            assert payload.get("residentAverageTransitDuration") == 600  # 10 min

            # ShortTermVisitor fields
            assert payload.get("shortTermVisitorCount") == 1


# =======================================================================
# --- JOB TESTS ---
# =======================================================================


class TestCrowdFlowsMunicipalityAllJob:
    """Test suite for the CrowdFlowsMunicipalityAll job class."""

    def test_job_normalizes_dates_to_hour_start(self, mock_main_db):
        """Test that dates are normalized to hour boundaries."""
        request = AllCrowdFlowsMunicipalityRequest(
            start_date=datetime(2023, 1, 1, 10, 30, 45),
            end_date=datetime(2023, 1, 1, 12, 45, 30),
        )

        sample_entities = [_create_entity(1, "sensor-01", "Sensor Alpha")]

        with patch("tasks.crowd.flows_municipality_job.delay") as mock_delay:
            job = CrowdFlowsMunicipalityAll(request=request, db=mock_main_db)
            job._CrowdFlowsMunicipalityAll__start_jobs(
                user_id=1, entities=sample_entities
            )

            # All delayed requests should have normalized dates
            for call_args in mock_delay.call_args_list:
                req = call_args[0][0]
                start_date = _get_datetime_from_request(req, "start_date")
                end_date = _get_datetime_from_request(req, "end_date")

                assert start_date.minute == 0
                assert start_date.second == 0
                assert start_date.microsecond == 0
                assert end_date.minute == 0
                assert end_date.second == 0
                assert end_date.microsecond == 0

    def test_job_creates_hourly_windows(self, mock_main_db):
        """Test that jobs are queued in 1-hour windows."""
        request = AllCrowdFlowsMunicipalityRequest(
            start_date=datetime(2023, 1, 1, 10, 0, 0),
            end_date=datetime(2023, 1, 1, 13, 0, 0),
        )

        sample_entities = [_create_entity(1, "sensor-01", "Sensor Alpha")]

        with patch("tasks.crowd.flows_municipality_job.delay") as mock_delay:
            job = CrowdFlowsMunicipalityAll(request=request, db=mock_main_db)
            job._CrowdFlowsMunicipalityAll__start_jobs(
                user_id=1, entities=sample_entities
            )

            # Should create 3 hourly windows: 10-11, 11-12, 12-13
            assert mock_delay.call_count == 3

            # Verify window boundaries
            expected_windows = [
                (datetime(2023, 1, 1, 10, 0), datetime(2023, 1, 1, 11, 0)),
                (datetime(2023, 1, 1, 11, 0), datetime(2023, 1, 1, 12, 0)),
                (datetime(2023, 1, 1, 12, 0), datetime(2023, 1, 1, 13, 0)),
            ]

            for i, call_args in enumerate(mock_delay.call_args_list):
                req = call_args[0][0]
                start_date = _get_datetime_from_request(req, "start_date")
                end_date = _get_datetime_from_request(req, "end_date")

                assert start_date == expected_windows[i][0]
                assert end_date == expected_windows[i][1]

    def test_job_sets_tourism_mode(self, mock_main_db):
        """Test that all queued jobs have tourism mode set."""
        request = AllCrowdFlowsMunicipalityRequest(
            start_date=datetime(2023, 1, 1, 10, 0, 0),
            end_date=datetime(2023, 1, 1, 12, 0, 0),
        )

        sample_entities = [_create_entity(1, "sensor-01", "Sensor Alpha")]

        with patch("tasks.crowd.flows_municipality_job.delay") as mock_delay:
            job = CrowdFlowsMunicipalityAll(request=request, db=mock_main_db)
            job._CrowdFlowsMunicipalityAll__start_jobs(
                user_id=1, entities=sample_entities
            )

            for call_args in mock_delay.call_args_list:
                req = call_args[0][0]
                assert req.mode == "tourism"

    def test_job_uses_default_dates_when_not_provided(self, mock_main_db):
        """Test that job uses default dates when start/end not provided."""
        request = AllCrowdFlowsMunicipalityRequest(
            start_date=None,
            end_date=None,
        )

        sample_entities = [_create_entity(1, "sensor-01", "Sensor Alpha")]

        with patch("tasks.crowd.flows_municipality_job.delay") as mock_delay:
            with patch(
                "jobs.crowd.all_crowd_flows_municipality_jobs.datetime"
            ) as mock_datetime:
                mock_now = datetime(2023, 1, 15, 14, 30, 45)
                mock_datetime.now.return_value = mock_now
                mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                    *args, **kwargs
                )

                job = CrowdFlowsMunicipalityAll(request=request, db=mock_main_db)
                job._CrowdFlowsMunicipalityAll__start_jobs(
                    user_id=1, entities=sample_entities
                )

                # Should have been called with default date range
                assert mock_delay.call_count >= 1

    def test_job_passes_entities_to_request(self, mock_main_db):
        """Test that entities are correctly passed to each job request."""
        request = AllCrowdFlowsMunicipalityRequest(
            start_date=datetime(2023, 1, 1, 10, 0, 0),
            end_date=datetime(2023, 1, 1, 11, 0, 0),
        )

        sample_entities = [
            _create_entity(1, "sensor-01", "Sensor Alpha"),
            _create_entity(2, "sensor-02", "Sensor Beta"),
        ]

        with patch("tasks.crowd.flows_municipality_job.delay") as mock_delay:
            job = CrowdFlowsMunicipalityAll(request=request, db=mock_main_db)
            job._CrowdFlowsMunicipalityAll__start_jobs(
                user_id=1, entities=sample_entities
            )

            assert mock_delay.call_count == 1
            req = mock_delay.call_args[0][0]

            assert len(req.entities) == 2
