import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# --- Schemas ---
from schemas.crowd_process_visitors_request_schema import (
    AllProcessVisitorsRequest,
    ProcessVisitorsRequest,
    ProcessVisitorsEntity,
)

# --- Classes Under Test ---
from etls.crowd.crowd_process_visitors_etl.transform.crowd_process_visitors_transform import (
    ProcessVisitorsTransform,
)
from etls.crowd.crowd_process_visitors_etl.load.crowd_process_visitors_load import (
    ProcessVisitorsLoad,
)

# --- Job ---
from jobs.crowd.all_crowd_process_vistors_jobs import ProcessVisitorsAll


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
    """Factory function to create ProcessVisitorsEntity."""
    return ProcessVisitorsEntity(
        id=entity_id,
        urn=f"urn:ngsi-ld:CrowdFlowEvent:{urn_suffix}",
        tenant="pid",
        scope="/",
        name=name,
    )


# =======================================================================
# --- FIXTURES ---
# =======================================================================


@pytest.fixture
def sample_entities():
    """Provides sample entity data."""
    return [
        _create_entity(1, "sensor-01_CFE", "Sensor Alpha"),
        _create_entity(2, "sensor-02_CFE", "Sensor Beta"),
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
        "aggregation_mode": "none",
    }


@pytest.fixture
def sample_raw_data():
    """Provides sample raw DataFrame for transform testing."""
    return pd.DataFrame(
        {
            "entityid": [
                "urn:ngsi-ld:CrowdFlowEvent:sensor-01_CFE",
                "urn:ngsi-ld:CrowdFlowEvent:sensor-01_CFE",
                "urn:ngsi-ld:CrowdFlowEvent:sensor-01_CFE",
                "urn:ngsi-ld:CrowdFlowEvent:sensor-02_CFE",
                "urn:ngsi-ld:CrowdFlowEvent:sensor-02_CFE",
            ],
            "visitorid": ["v1", "v1", "v2", "v2", "v1"],
            "timeinstant": [
                datetime(2023, 1, 1, 10, 0),
                datetime(2023, 1, 1, 10, 30),
                datetime(2023, 1, 1, 10, 5),
                datetime(2023, 1, 1, 10, 20),
                datetime(2023, 1, 1, 10, 45),
            ],
        }
    )


@pytest.fixture
def timeseries_data_camelcase():
    """
    Sample data as it comes from get_time_series_in_df_format.
    This is the format that crowd_df_columns_rename receives.
    """
    return pd.DataFrame(
        {
            "timeinstant": [
                "2025-01-24T07:40:02",
                "2025-01-24T07:41:02",
                "2025-01-24T07:50:03",
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
                "4058078681d489017524688c6f111fa0bd0d288f",
                "4058078681d489017524688c6f111fa0bd0d288f",
                "0bf0ae029a5ebafcbf7dabe36785bbb0c6ea8895",
                "aa4c22906b0f6c5cd3c5992e590328dfbb94e187",
            ],
        }
    )


@pytest.fixture
def sample_transform_output():
    """Provides sample transform output for load testing."""
    return {
        "result": pd.DataFrame(
            {
                "entityid": ["urn:ngsi-ld:CrowdFlowEvent:sensor-01_CFE"],
                "visits": [5],
                "unique_visitors": [3],
                "averagevisitduration": [timedelta(minutes=15)],
                "minimumvisitduration": [timedelta(minutes=5)],
                "maximumvisitduration": [timedelta(minutes=30)],
                "touristvisits": [2],
                "tourist_unique_visitors": [1],
                "touristaveragevisitduration": [timedelta(minutes=20)],
                "touristminimumvisitduration": [timedelta(minutes=15)],
                "touristmaximumvisitduration": [timedelta(minutes=25)],
                "residentvisits": [2],
                "resident_unique_visitors": [1],
                "residentaveragevisitduration": [timedelta(minutes=10)],
                "residentminimumvisitduration": [timedelta(minutes=5)],
                "residentmaximumvisitduration": [timedelta(minutes=15)],
                "shorttermvisitorvisits": [1],
                "shorttermvisitor_unique_visitors": [1],
                "shorttermvisitoraveragevisitduration": [timedelta(minutes=5)],
                "shorttermvisitorminimumvisitduration": [timedelta(minutes=5)],
                "shorttermvisitormaximumvisitduration": [timedelta(minutes=5)],
            }
        )
    }


# =======================================================================
# --- TRANSFORM TESTS ---
# =======================================================================


class TestProcessVisitorsTransform:
    """Test suite for the ProcessVisitorsTransform class."""

    def test_transform_calculates_visit_duration(
        self, base_request_params, mock_main_db, mock_realtime_db
    ):
        """Test that transform correctly calculates visit duration."""
        request = ProcessVisitorsRequest(**base_request_params)

        # Visitor v1 visits sensor-01 from 10:00 to 10:30
        raw_data = pd.DataFrame(
            {
                "entityid": [
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-01_CFE",
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-01_CFE",
                ],
                "visitorid": ["v1", "v1"],
                "timeinstant": [
                    datetime(2023, 1, 1, 10, 0),
                    datetime(2023, 1, 1, 10, 30),
                ],
            }
        )

        extract_output = {
            "df_raw": raw_data,
            "visitors": ["v1"],
            "previous_visitor_types": {"v1": "Resident"},
        }

        transformer = ProcessVisitorsTransform(
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
        request = ProcessVisitorsRequest(**base_request_params)

        raw_data = pd.DataFrame(
            {
                "entityid": [
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-01_CFE",
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-01_CFE",
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-01_CFE",
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-01_CFE",
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

        transformer = ProcessVisitorsTransform(
            request=request,
            extract_output=extract_output,
            main_db=mock_main_db,
            realtime_db=mock_realtime_db,
        )

        result = transformer.transform()
        result_df = result["result"]

        # Should have tourist and resident visits
        assert "touristvisits" in result_df.columns
        assert "residentvisits" in result_df.columns

    def test_transform_unknown_visitors_classified_as_short_term(
        self, base_request_params, mock_main_db, mock_realtime_db
    ):
        """Test that unknown visitors are classified as ShortTermVisitor."""
        request = ProcessVisitorsRequest(**base_request_params)

        raw_data = pd.DataFrame(
            {
                "entityid": [
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-01_CFE",
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-01_CFE",
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

        transformer = ProcessVisitorsTransform(
            request=request,
            extract_output=extract_output,
            main_db=mock_main_db,
            realtime_db=mock_realtime_db,
        )

        result = transformer.transform()
        result_df = result["result"]

        # ShortTermVisitor visits should be present
        assert "shorttermvisitorvisits" in result_df.columns

    def test_transform_calculates_unique_visitors(
        self, base_request_params, mock_main_db, mock_realtime_db
    ):
        """Test that transform calculates unique visitors per entity."""
        request = ProcessVisitorsRequest(**base_request_params)

        # 3 unique visitors at sensor-01
        raw_data = pd.DataFrame(
            {
                "entityid": [
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-01_CFE",
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-01_CFE",
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-01_CFE",
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-01_CFE",
                ],
                "visitorid": ["v1", "v1", "v2", "v3"],
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
            "visitors": ["v1", "v2", "v3"],
            "previous_visitor_types": {},
        }

        transformer = ProcessVisitorsTransform(
            request=request,
            extract_output=extract_output,
            main_db=mock_main_db,
            realtime_db=mock_realtime_db,
        )

        result = transformer.transform()
        result_df = result["result"]

        assert "unique_visitors" in result_df.columns
        assert result_df["unique_visitors"].iloc[0] == 3

    def test_transform_calculates_visit_duration_statistics(
        self, base_request_params, mock_main_db, mock_realtime_db
    ):
        """Test that transform calculates avg, min, max visit durations."""
        request = ProcessVisitorsRequest(**base_request_params)

        raw_data = pd.DataFrame(
            {
                "entityid": [
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-01_CFE",
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-01_CFE",
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-01_CFE",
                    "urn:ngsi-ld:CrowdFlowEvent:sensor-01_CFE",
                ],
                "visitorid": ["v1", "v1", "v2", "v2"],
                "timeinstant": [
                    datetime(2023, 1, 1, 10, 0),
                    datetime(2023, 1, 1, 10, 10),  # v1: 10 min visit
                    datetime(2023, 1, 1, 10, 5),
                    datetime(2023, 1, 1, 10, 25),  # v2: 20 min visit
                ],
            }
        )

        extract_output = {
            "df_raw": raw_data,
            "visitors": ["v1", "v2"],
            "previous_visitor_types": {"v1": "Tourist", "v2": "Tourist"},
        }

        transformer = ProcessVisitorsTransform(
            request=request,
            extract_output=extract_output,
            main_db=mock_main_db,
            realtime_db=mock_realtime_db,
        )

        result = transformer.transform()
        result_df = result["result"]

        # Should have duration statistics
        assert "averagevisitduration" in result_df.columns
        assert "minimumvisitduration" in result_df.columns
        assert "maximumvisitduration" in result_df.columns


# =======================================================================
# --- LOAD TESTS ---
# =======================================================================


class TestProcessVisitorsLoad:
    """Test suite for the ProcessVisitorsLoad class."""

    def test_load_converts_timedelta_to_seconds(
        self, base_request_params, mock_main_db, mock_realtime_db
    ):
        """Test that timedelta values are converted to seconds in payload."""
        request = ProcessVisitorsRequest(**base_request_params)

        transform_output = {
            "result": pd.DataFrame(
                {
                    "entityid": ["urn:ngsi-ld:CrowdFlowEvent:sensor-01_CFE"],
                    "visits": [5],
                    "unique_visitors": [3],
                    "averagevisitduration": [timedelta(minutes=15)],
                    "minimumvisitduration": [timedelta(minutes=5)],
                    "maximumvisitduration": [timedelta(minutes=30)],
                    "touristvisits": [2],
                    "tourist_unique_visitors": [1],
                    "touristaveragevisitduration": [timedelta(minutes=20)],
                    "touristminimumvisitduration": [timedelta(minutes=15)],
                    "touristmaximumvisitduration": [timedelta(minutes=25)],
                    "residentvisits": [2],
                    "resident_unique_visitors": [1],
                    "residentaveragevisitduration": [timedelta(minutes=10)],
                    "residentminimumvisitduration": [timedelta(minutes=5)],
                    "residentmaximumvisitduration": [timedelta(minutes=15)],
                    "shorttermvisitorvisits": [1],
                    "shorttermvisitor_unique_visitors": [1],
                    "shorttermvisitoraveragevisitduration": [timedelta(minutes=5)],
                    "shorttermvisitorminimumvisitduration": [timedelta(minutes=5)],
                    "shorttermvisitormaximumvisitduration": [timedelta(minutes=5)],
                }
            )
        }

        with patch(
            "etls.crowd.crowd_process_visitors_etl.load.crowd_process_visitors_load.iota_helper.publish_data"
        ) as mock_publish, patch(
            "etls.crowd.crowd_process_visitors_etl.load.crowd_process_visitors_load.crud_preferences.get_user_preference",
            return_value=1,
        ), patch(
            "etls.crowd.crowd_process_visitors_etl.load.crowd_process_visitors_load.crud_tenant_scope.get_tenant_scope",
            return_value=("pid", "/"),
        ), patch(
            "etls.crowd.crowd_process_visitors_etl.load.crowd_process_visitors_load.aether_link_helper.get_iota_services",
            return_value=[{"apikey": "test-key", "resource": "/"}],
        ):
            loader = ProcessVisitorsLoad(
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
            assert payload.get("averageVisitDuration") == 900
            # 5 minutes = 300 seconds
            assert payload.get("minimumVisitDuration") == 300
            # 30 minutes = 1800 seconds
            assert payload.get("maximumVisitDuration") == 1800


    def test_load_includes_classification_fields(
        self, base_request_params, mock_main_db, mock_realtime_db
    ):
        """Test that classification-specific fields are included in payload."""
        request = ProcessVisitorsRequest(**base_request_params)

        transform_output = {
            "result": pd.DataFrame(
                {
                    "entityid": ["urn:ngsi-ld:CrowdFlowEvent:sensor-01_CFE"],
                    "visits": [10],
                    "unique_visitors": [5],
                    "averagevisitduration": [timedelta(minutes=15)],
                    "minimumvisitduration": [timedelta(minutes=5)],
                    "maximumvisitduration": [timedelta(minutes=30)],
                    "touristvisits": [4],
                    "tourist_unique_visitors": [2],
                    "touristaveragevisitduration": [timedelta(minutes=20)],
                    "touristminimumvisitduration": [timedelta(minutes=10)],
                    "touristmaximumvisitduration": [timedelta(minutes=30)],
                    "residentvisits": [4],
                    "resident_unique_visitors": [2],
                    "residentaveragevisitduration": [timedelta(minutes=10)],
                    "residentminimumvisitduration": [timedelta(minutes=5)],
                    "residentmaximumvisitduration": [timedelta(minutes=15)],
                    "shorttermvisitorvisits": [2],
                    "shorttermvisitor_unique_visitors": [1],
                    "shorttermvisitoraveragevisitduration": [timedelta(minutes=5)],
                    "shorttermvisitorminimumvisitduration": [timedelta(minutes=5)],
                    "shorttermvisitormaximumvisitduration": [timedelta(minutes=5)],
                }
            )
        }

        with patch(
            "etls.crowd.crowd_process_visitors_etl.load.crowd_process_visitors_load.iota_helper.publish_data"
        ) as mock_publish, patch(
            "etls.crowd.crowd_process_visitors_etl.load.crowd_process_visitors_load.crud_preferences.get_user_preference",
            return_value=1,
        ), patch(
            "etls.crowd.crowd_process_visitors_etl.load.crowd_process_visitors_load.crud_tenant_scope.get_tenant_scope",
            return_value=("pid", "/"),
        ), patch(
            "etls.crowd.crowd_process_visitors_etl.load.crowd_process_visitors_load.aether_link_helper.get_iota_services",
            return_value=[{"apikey": "test-key", "resource": "/"}],
        ):
            loader = ProcessVisitorsLoad(
                request=request,
                transform_output=transform_output,
                main_db=mock_main_db,
                realtime_db=mock_realtime_db,
            )
            loader.load()

            mock_publish.assert_called_once()
            payload = mock_publish.call_args[1].get("body")

            # Tourist fields
            assert payload.get("touristVisits") == 4
            assert payload.get("touristUniqueVisitors") == 2
            assert payload.get("touristAverageVisitDuration") == 1200  # 20 min

            # Resident fields
            assert payload.get("residentVisits") == 4
            assert payload.get("residentUniqueVisitors") == 2
            assert payload.get("residentAverageVisitDuration") == 600  # 10 min

            # ShortTermVisitor fields
            assert payload.get("shortTermVisitorVisits") == 2
            assert payload.get("shortTermVisitorUniqueVisitors") == 1

    def test_load_includes_date_fields(
        self, base_request_params, mock_main_db, mock_realtime_db
    ):
        """Test that start/end date fields are included in payload."""
        request = ProcessVisitorsRequest(**base_request_params)

        transform_output = {
            "result": pd.DataFrame(
                {
                    "entityid": ["urn:ngsi-ld:CrowdFlowEvent:sensor-01_CFE"],
                    "visits": [5],
                    "unique_visitors": [3],
                    "averagevisitduration": [timedelta(minutes=15)],
                    "minimumvisitduration": [timedelta(minutes=5)],
                    "maximumvisitduration": [timedelta(minutes=30)],
                    "touristvisits": [2],
                    "tourist_unique_visitors": [1],
                    "touristaveragevisitduration": [timedelta(minutes=20)],
                    "touristminimumvisitduration": [timedelta(minutes=15)],
                    "touristmaximumvisitduration": [timedelta(minutes=25)],
                    "residentvisits": [2],
                    "resident_unique_visitors": [1],
                    "residentaveragevisitduration": [timedelta(minutes=10)],
                    "residentminimumvisitduration": [timedelta(minutes=5)],
                    "residentmaximumvisitduration": [timedelta(minutes=15)],
                    "shorttermvisitorvisits": [1],
                    "shorttermvisitor_unique_visitors": [1],
                    "shorttermvisitoraveragevisitduration": [timedelta(minutes=5)],
                    "shorttermvisitorminimumvisitduration": [timedelta(minutes=5)],
                    "shorttermvisitormaximumvisitduration": [timedelta(minutes=5)],
                }
            )
        }

        with patch(
            "etls.crowd.crowd_process_visitors_etl.load.crowd_process_visitors_load.iota_helper.publish_data"
        ) as mock_publish, patch(
            "etls.crowd.crowd_process_visitors_etl.load.crowd_process_visitors_load.crud_preferences.get_user_preference",
            return_value=1,
        ), patch(
            "etls.crowd.crowd_process_visitors_etl.load.crowd_process_visitors_load.crud_tenant_scope.get_tenant_scope",
            return_value=("pid", "/"),
        ), patch(
            "etls.crowd.crowd_process_visitors_etl.load.crowd_process_visitors_load.aether_link_helper.get_iota_services",
            return_value=[{"apikey": "test-key", "resource": "/"}],
        ):
            loader = ProcessVisitorsLoad(
                request=request,
                transform_output=transform_output,
                main_db=mock_main_db,
                realtime_db=mock_realtime_db,
            )
            loader.load()

            mock_publish.assert_called_once()
            payload = mock_publish.call_args[1].get("body")

            assert "startDate" in payload
            assert "endDate" in payload
            assert "TimeInstant" in payload
            assert payload["startDate"] == "2023-01-01T10:00:00"
            assert payload["endDate"] == "2023-01-01T11:00:00"

# =======================================================================
# --- HELPER FUNCTIONS ---
# =======================================================================


def _get_datetime_from_request(request_obj, attr_name="end_date"):
    """Helper to extract datetime from request, handling both datetime and ISO string."""
    value = getattr(request_obj, attr_name)
    return value if isinstance(value, datetime) else datetime.fromisoformat(value)


# =======================================================================
# --- JOB TESTS ---
# =======================================================================


class TestProcessVisitorsAllJob:
    """Test suite for the ProcessVisitorsAll job class."""

    def test_job_normalizes_dates_to_hour_start(self, mock_main_db):
        """Test that dates are normalized to hour boundaries."""
        request = AllProcessVisitorsRequest(
            start_date=datetime(2023, 1, 1, 10, 30, 45),
            end_date=datetime(2023, 1, 1, 12, 45, 30),
        )

        sample_entities = [_create_entity(1, "sensor-01_CFE", "Sensor Alpha")]

        with patch("tasks.crowd.process_visitors_job.delay") as mock_delay:
            job = ProcessVisitorsAll(request=request, db=mock_main_db)
            job._ProcessVisitorsAll__start_jobs(
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
        request = AllProcessVisitorsRequest(
            start_date=datetime(2023, 1, 1, 10, 0, 0),
            end_date=datetime(2023, 1, 1, 13, 0, 0),
        )

        sample_entities = [_create_entity(1, "sensor-01_CFE", "Sensor Alpha")]

        with patch("tasks.crowd.process_visitors_job.delay") as mock_delay:
            job = ProcessVisitorsAll(request=request, db=mock_main_db)
            job._ProcessVisitorsAll__start_jobs(
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
        request = AllProcessVisitorsRequest(
            start_date=datetime(2023, 1, 1, 10, 0, 0),
            end_date=datetime(2023, 1, 1, 12, 0, 0),
        )

        sample_entities = [_create_entity(1, "sensor-01_CFE", "Sensor Alpha")]

        with patch("tasks.crowd.process_visitors_job.delay") as mock_delay:
            job = ProcessVisitorsAll(request=request, db=mock_main_db)
            job._ProcessVisitorsAll__start_jobs(
                user_id=1, entities=sample_entities
            )

            for call_args in mock_delay.call_args_list:
                req = call_args[0][0]
                assert req.mode == "tourism"

    def test_job_sets_aggregation_mode_none(self, mock_main_db):
        """Test that all queued jobs have aggregation_mode set to none."""
        request = AllProcessVisitorsRequest(
            start_date=datetime(2023, 1, 1, 10, 0, 0),
            end_date=datetime(2023, 1, 1, 12, 0, 0),
        )

        sample_entities = [_create_entity(1, "sensor-01_CFE", "Sensor Alpha")]

        with patch("tasks.crowd.process_visitors_job.delay") as mock_delay:
            job = ProcessVisitorsAll(request=request, db=mock_main_db)
            job._ProcessVisitorsAll__start_jobs(
                user_id=1, entities=sample_entities
            )

            for call_args in mock_delay.call_args_list:
                req = call_args[0][0]
                assert req.aggregation_mode == "none"

    def test_job_uses_default_dates_when_not_provided(self, mock_main_db):
        """Test that job uses default dates when start/end not provided."""
        request = AllProcessVisitorsRequest(
            start_date=None,
            end_date=None,
        )

        sample_entities = [_create_entity(1, "sensor-01_CFE", "Sensor Alpha")]

        with patch("tasks.crowd.process_visitors_job.delay") as mock_delay:
            with patch(
                "jobs.crowd.all_crowd_process_vistors_jobs.datetime"
            ) as mock_datetime:
                mock_now = datetime(2023, 1, 15, 14, 30, 45)
                mock_datetime.now.return_value = mock_now
                mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                    *args, **kwargs
                )

                job = ProcessVisitorsAll(request=request, db=mock_main_db)
                job._ProcessVisitorsAll__start_jobs(
                    user_id=1, entities=sample_entities
                )

                # Should have been called with default date range
                assert mock_delay.call_count >= 1

    def test_job_passes_entities_to_request(self, mock_main_db):
        """Test that entities are correctly passed to each job request."""
        request = AllProcessVisitorsRequest(
            start_date=datetime(2023, 1, 1, 10, 0, 0),
            end_date=datetime(2023, 1, 1, 11, 0, 0),
        )

        sample_entities = [
            _create_entity(1, "sensor-01_CFE", "Sensor Alpha"),
            _create_entity(2, "sensor-02_CFE", "Sensor Beta"),
        ]

        with patch("tasks.crowd.process_visitors_job.delay") as mock_delay:
            job = ProcessVisitorsAll(request=request, db=mock_main_db)
            job._ProcessVisitorsAll__start_jobs(
                user_id=1, entities=sample_entities
            )

            assert mock_delay.call_count == 1
            req = mock_delay.call_args[0][0]

            assert len(req.entities) == 2

    def test_job_handles_single_hour_window(self, mock_main_db):
        """Test that job correctly handles a single hour window."""
        request = AllProcessVisitorsRequest(
            start_date=datetime(2023, 1, 1, 10, 0, 0),
            end_date=datetime(2023, 1, 1, 11, 0, 0),
        )

        sample_entities = [_create_entity(1, "sensor-01_CFE", "Sensor Alpha")]

        with patch("tasks.crowd.process_visitors_job.delay") as mock_delay:
            job = ProcessVisitorsAll(request=request, db=mock_main_db)
            job._ProcessVisitorsAll__start_jobs(
                user_id=1, entities=sample_entities
            )

            # Should create exactly 1 hourly window
            assert mock_delay.call_count == 1

            req = mock_delay.call_args[0][0]
            start_date = _get_datetime_from_request(req, "start_date")
            end_date = _get_datetime_from_request(req, "end_date")

            assert start_date == datetime(2023, 1, 1, 10, 0, 0)
            assert end_date == datetime(2023, 1, 1, 11, 0, 0)

    def test_job_handles_multi_day_range(self, mock_main_db):
        """Test that job correctly handles a multi-day date range."""
        request = AllProcessVisitorsRequest(
            start_date=datetime(2023, 1, 1, 10, 0, 0),
            end_date=datetime(2023, 1, 2, 10, 0, 0),  # 24 hours later
        )

        sample_entities = [_create_entity(1, "sensor-01_CFE", "Sensor Alpha")]

        with patch("tasks.crowd.process_visitors_job.delay") as mock_delay:
            job = ProcessVisitorsAll(request=request, db=mock_main_db)
            job._ProcessVisitorsAll__start_jobs(
                user_id=1, entities=sample_entities
            )

            # Should create 24 hourly windows
            assert mock_delay.call_count == 24
