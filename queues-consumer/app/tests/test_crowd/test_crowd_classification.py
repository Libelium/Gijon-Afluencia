"""
Tests for Classification ETL.

This file contains tests specific to the Classification ETL extraction phase
that are not common with other crowd ETLs.

Classification ETL differences:
- Returns bool from extract() instead of dict
- Stores data internally: self.df_raw, self.visitors, self.previous_visitor_types
- Uses mode "monthly" or "weekly" instead of "tourism"
"""

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# --- Schemas ---
from schemas.crowd_classification_request_schema import (
    AllCrowdClassificationRequest,
    CrowdClassificationRequest,
    CrowdClassificationEntity,
)

# --- ETL ---
from etls.crowd.crowd_classification_etl.etl import CrowdClassificationETL

# --- Job ---
from jobs.crowd.all_crowd_classification_jobs import CrowdClassificationAll


@pytest.fixture
def mock_main_db():
    """Provides a mock for the Platform DB session."""
    return MagicMock()


@pytest.fixture
def mock_realtime_db():
    """Provides a mock for the Realtime DB session."""
    return MagicMock()


def _create_entity(entity_id: int, urn_suffix: str, name: str = None):
    return CrowdClassificationEntity(
        id=entity_id,
        urn=f"urn:ngsi-ld:CrowdFlowEvent:{urn_suffix}",
        tenant="pid",
        scope="/",
        name=name,
    )


@pytest.fixture
def sample_entities():
    """Provides sample entity data."""
    return [_create_entity(1, "sensor-01_CFE", "Sensor Alpha")]


@pytest.fixture
def base_request_params(sample_entities):
    """Provides base parameters for creating a request."""
    return {
        "entities": sample_entities,
        "start_date": datetime(2023, 1, 1, 10, 0, 0),
        "end_date": datetime(2023, 1, 31, 11, 0, 0),
        "user_id": 1,
        "mode": "monthly",
    }


@pytest.fixture
def timeseries_data_camelcase():
    """Sample data as it comes from get_time_series_in_df_format."""
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


# =======================================================================
# --- EXTRACTION TESTS (Classification-specific) ---
# =======================================================================


class TestClassificationExtract:
    """Tests specific to Classification ETL extraction phase."""

    def test_extract_returns_bool_true_on_success(
        self, base_request_params, timeseries_data_camelcase, mock_main_db, mock_realtime_db
    ):
        """Test that extract returns True on successful extraction."""
        request = CrowdClassificationRequest(**base_request_params)

        with patch(
            "etls.crowd.crowd_classification_etl.etl.aether_link_helper.get_time_series_in_df_format",
            return_value=timeseries_data_camelcase,
        ), patch(
            "etls.crowd.crowd_classification_etl.etl.get_user_crowd_visitor",
            return_value=[],
        ):
            etl = CrowdClassificationETL(
                request=request,
                main_db=mock_main_db,
                realtime_db=mock_realtime_db,
            )

            result = etl.extract()

            assert result is True

    def test_extract_returns_false_on_empty_data(
        self, base_request_params, mock_main_db, mock_realtime_db
    ):
        """Test that extract returns False when no data is available."""
        request = CrowdClassificationRequest(**base_request_params)

        with patch(
            "etls.crowd.crowd_classification_etl.etl.aether_link_helper.get_time_series_in_df_format",
            return_value=pd.DataFrame(),
        ), patch(
            "etls.crowd.crowd_classification_etl.etl.get_user_crowd_visitor",
            return_value=[],
        ):
            etl = CrowdClassificationETL(
                request=request,
                main_db=mock_main_db,
                realtime_db=mock_realtime_db,
            )

            result = etl.extract()

            assert result is False

    def test_extract_stores_visitors_internally(
        self, base_request_params, timeseries_data_camelcase, mock_main_db, mock_realtime_db
    ):
        """Test that visitors are stored internally after extract."""
        request = CrowdClassificationRequest(**base_request_params)

        with patch(
            "etls.crowd.crowd_classification_etl.etl.aether_link_helper.get_time_series_in_df_format",
            return_value=timeseries_data_camelcase,
        ), patch(
            "etls.crowd.crowd_classification_etl.etl.get_user_crowd_visitor",
            return_value=[],
        ):
            etl = CrowdClassificationETL(
                request=request,
                main_db=mock_main_db,
                realtime_db=mock_realtime_db,
            )

            etl.extract()

            assert etl.visitors is not None
            assert len(etl.visitors) == 3  # 3 unique visitors in test data

    def test_extract_stores_df_raw_internally(
        self, base_request_params, timeseries_data_camelcase, mock_main_db, mock_realtime_db
    ):
        """Test that df_raw is stored internally after extract."""
        request = CrowdClassificationRequest(**base_request_params)

        with patch(
            "etls.crowd.crowd_classification_etl.etl.aether_link_helper.get_time_series_in_df_format",
            return_value=timeseries_data_camelcase,
        ), patch(
            "etls.crowd.crowd_classification_etl.etl.get_user_crowd_visitor",
            return_value=[],
        ):
            etl = CrowdClassificationETL(
                request=request,
                main_db=mock_main_db,
                realtime_db=mock_realtime_db,
            )

            etl.extract()

            assert etl.df_raw is not None
            assert not etl.df_raw.empty

    def test_extract_stores_previous_visitor_types_internally(
        self, base_request_params, timeseries_data_camelcase, mock_main_db, mock_realtime_db
    ):
        """Test that previous visitor types are stored internally."""
        request = CrowdClassificationRequest(**base_request_params)

        mock_visitor = MagicMock()
        mock_visitor.visitor_id = "visitor_001"
        mock_visitor.visitor_type = "Resident"

        with patch(
            "etls.crowd.crowd_classification_etl.etl.aether_link_helper.get_time_series_in_df_format",
            return_value=timeseries_data_camelcase,
        ), patch(
            "etls.crowd.crowd_classification_etl.etl.get_user_crowd_visitor",
            return_value=[mock_visitor],
        ):
            etl = CrowdClassificationETL(
                request=request,
                main_db=mock_main_db,
                realtime_db=mock_realtime_db,
            )

            etl.extract()

            assert etl.previous_visitor_types is not None
            assert "visitor_001" in etl.previous_visitor_types
            assert etl.previous_visitor_types["visitor_001"] == "Resident"

    def test_extract_normalizes_columns(
        self, base_request_params, timeseries_data_camelcase, mock_main_db, mock_realtime_db
    ):
        """Test that columns are normalized to lowercase after extract."""
        request = CrowdClassificationRequest(**base_request_params)

        with patch(
            "etls.crowd.crowd_classification_etl.etl.aether_link_helper.get_time_series_in_df_format",
            return_value=timeseries_data_camelcase,
        ), patch(
            "etls.crowd.crowd_classification_etl.etl.get_user_crowd_visitor",
            return_value=[],
        ):
            etl = CrowdClassificationETL(
                request=request,
                main_db=mock_main_db,
                realtime_db=mock_realtime_db,
            )

            etl.extract()

            df = etl.df_raw
            # Check columns are normalized to lowercase
            assert "entityid" in df.columns
            assert "visitorid" in df.columns
            assert "detectiontype" in df.columns
            assert "israndommac" in df.columns

    @pytest.mark.parametrize("mode", ["monthly", "weekly"])
    def test_extract_supports_monthly_and_weekly_modes(
        self, sample_entities, timeseries_data_camelcase, mock_main_db, mock_realtime_db, mode
    ):
        """Test that extract supports both monthly and weekly modes."""
        request = CrowdClassificationRequest(
            entities=sample_entities,
            start_date=datetime(2023, 1, 1, 10, 0, 0),
            end_date=datetime(2023, 1, 31, 11, 0, 0),
            user_id=1,
            mode=mode,
        )

        with patch(
            "etls.crowd.crowd_classification_etl.etl.aether_link_helper.get_time_series_in_df_format",
            return_value=timeseries_data_camelcase,
        ), patch(
            "etls.crowd.crowd_classification_etl.etl.get_user_crowd_visitor",
            return_value=[],
        ):
            etl = CrowdClassificationETL(
                request=request,
                main_db=mock_main_db,
                realtime_db=mock_realtime_db,
            )

            result = etl.extract()

            assert result is True


# =======================================================================
# --- HELPER FUNCTIONS ---
# =======================================================================


def _get_datetime_from_request(request_obj, attr_name="end_date"):
    """Helper to extract datetime from request, handling both datetime and ISO string."""
    value = getattr(request_obj, attr_name)
    return value if isinstance(value, datetime) else datetime.fromisoformat(value)




# =======================================================================
# --- TRANSFORM TESTS ---
# =======================================================================


class TestClassificationTransform:
    """Tests for Classification ETL transform phase."""

    @pytest.fixture
    def etl_with_extracted_data(
        self, base_request_params, mock_main_db, mock_realtime_db
    ):
        """Creates an ETL instance with data already extracted."""
        request = CrowdClassificationRequest(**base_request_params)
        etl = CrowdClassificationETL(
            request=request,
            main_db=mock_main_db,
            realtime_db=mock_realtime_db,
        )
        return etl

    def test_transform_classifies_visitor_as_resident_when_more_than_two_days(
        self, etl_with_extracted_data
    ):
        """Test visitor is classified as Resident when appearing on >2 days."""
        etl = etl_with_extracted_data
        # Visitor appears on 3 different days
        etl.df_raw = pd.DataFrame(
            {
                "timeinstant": [
                    "2023-01-01T10:00:00",
                    "2023-01-02T10:00:00",
                    "2023-01-03T10:00:00",
                ],
                "visitorid": ["visitor_001", "visitor_001", "visitor_001"],
            }
        )
        etl.visitors = ["visitor_001"]
        etl.previous_visitor_types = {}

        result = etl.transform()

        assert result is True
        assert etl.classified_visitors is not None
        visitor_type = etl.classified_visitors[
            etl.classified_visitors["visitorid"] == "visitor_001"
        ]["visitortype"].iloc[0]
        assert visitor_type == "Resident"

    def test_transform_classifies_visitor_as_resident_when_previously_resident(
        self, etl_with_extracted_data
    ):
        """Test visitor is classified as Resident when previously was Resident."""
        etl = etl_with_extracted_data
        # Visitor appears on only 1 day but was previously Resident
        etl.df_raw = pd.DataFrame(
            {
                "timeinstant": ["2023-01-01T10:00:00"],
                "visitorid": ["visitor_001"],
            }
        )
        etl.visitors = ["visitor_001"]
        etl.previous_visitor_types = {"visitor_001": "Resident"}

        result = etl.transform()

        assert result is True
        visitor_type = etl.classified_visitors[
            etl.classified_visitors["visitorid"] == "visitor_001"
        ]["visitortype"].iloc[0]
        assert visitor_type == "Resident"

    def test_transform_classifies_visitor_as_resident_when_previously_tourist(
        self, etl_with_extracted_data
    ):
        """Test visitor is classified as Resident when previously was Tourist."""
        etl = etl_with_extracted_data
        # Visitor appears on only 1 day but was previously Tourist
        etl.df_raw = pd.DataFrame(
            {
                "timeinstant": ["2023-01-01T10:00:00"],
                "visitorid": ["visitor_001"],
            }
        )
        etl.visitors = ["visitor_001"]
        etl.previous_visitor_types = {"visitor_001": "Tourist"}

        result = etl.transform()

        assert result is True
        visitor_type = etl.classified_visitors[
            etl.classified_visitors["visitorid"] == "visitor_001"
        ]["visitortype"].iloc[0]
        assert visitor_type == "Resident"

    def test_transform_classifies_visitor_as_tourist_when_short_stay_long_hours(
        self, etl_with_extracted_data
    ):
        """Test visitor is classified as Tourist when 1-2 days but >3 hours total."""
        etl = etl_with_extracted_data
        # Visitor appears on 1 day, spends 5 hours
        etl.df_raw = pd.DataFrame(
            {
                "timeinstant": [
                    "2023-01-01T08:00:00",
                    "2023-01-01T13:00:00",  # 5 hours later
                ],
                "visitorid": ["visitor_001", "visitor_001"],
            }
        )
        etl.visitors = ["visitor_001"]
        etl.previous_visitor_types = {}

        result = etl.transform()

        assert result is True
        visitor_type = etl.classified_visitors[
            etl.classified_visitors["visitorid"] == "visitor_001"
        ]["visitortype"].iloc[0]
        assert visitor_type == "Tourist"

    def test_transform_classifies_visitor_as_short_term_visitor(
        self, etl_with_extracted_data
    ):
        """Test visitor is classified as ShortTermVisitor when not meeting other criteria."""
        etl = etl_with_extracted_data
        # Visitor appears on 1 day, spends only 1 hour
        etl.df_raw = pd.DataFrame(
            {
                "timeinstant": [
                    "2023-01-01T10:00:00",
                    "2023-01-01T11:00:00",  # 1 hour later
                ],
                "visitorid": ["visitor_001", "visitor_001"],
            }
        )
        etl.visitors = ["visitor_001"]
        etl.previous_visitor_types = {}

        result = etl.transform()

        assert result is True
        visitor_type = etl.classified_visitors[
            etl.classified_visitors["visitorid"] == "visitor_001"
        ]["visitortype"].iloc[0]
        assert visitor_type == "ShortTermVisitor"

    def test_transform_handles_multiple_visitors_with_different_classifications(
        self, etl_with_extracted_data
    ):
        """Test transform correctly classifies multiple visitors with different behaviors."""
        etl = etl_with_extracted_data
        etl.df_raw = pd.DataFrame(
            {
                "timeinstant": [
                    # Resident: appears on 3 days
                    "2023-01-01T10:00:00",
                    "2023-01-02T10:00:00",
                    "2023-01-03T10:00:00",
                    # Tourist: 1 day, 5 hours
                    "2023-01-01T08:00:00",
                    "2023-01-01T13:00:00",
                    # ShortTermVisitor: 1 day, 1 hour
                    "2023-01-01T10:00:00",
                    "2023-01-01T11:00:00",
                ],
                "visitorid": [
                    "resident_001",
                    "resident_001",
                    "resident_001",
                    "tourist_001",
                    "tourist_001",
                    "short_term_001",
                    "short_term_001",
                ],
            }
        )
        etl.visitors = ["resident_001", "tourist_001", "short_term_001"]
        etl.previous_visitor_types = {}

        result = etl.transform()

        assert result is True
        assert len(etl.classified_visitors) == 3

        classifications = dict(
            zip(
                etl.classified_visitors["visitorid"],
                etl.classified_visitors["visitortype"],
            )
        )
        assert classifications["resident_001"] == "Resident"
        assert classifications["tourist_001"] == "Tourist"
        assert classifications["short_term_001"] == "ShortTermVisitor"


# =======================================================================
# --- LOAD TESTS ---
# =======================================================================


class TestClassificationLoad:
    """Tests for Classification ETL load phase."""

    @pytest.fixture
    def etl_with_classified_data(
        self, base_request_params, mock_main_db, mock_realtime_db
    ):
        """Creates an ETL instance with classified visitor data."""
        request = CrowdClassificationRequest(**base_request_params)
        etl = CrowdClassificationETL(
            request=request,
            main_db=mock_main_db,
            realtime_db=mock_realtime_db,
        )
        return etl

    def test_load_returns_true_on_success(self, etl_with_classified_data):
        """Test that load returns True on successful storage."""
        etl = etl_with_classified_data
        etl.classified_visitors = pd.DataFrame(
            {
                "visitorid": ["visitor_001"],
                "visitortype": ["Resident"],
            }
        )

        with patch(
            "etls.crowd.crowd_classification_etl.etl.create_or_update_crowd_visitors_batch"
        ) as mock_store:
            result = etl.load()

            assert result is True
            mock_store.assert_called_once()

    def test_load_filters_out_short_term_visitors(self, etl_with_classified_data):
        """Test that load only stores non-ShortTermVisitors."""
        etl = etl_with_classified_data
        etl.classified_visitors = pd.DataFrame(
            {
                "visitorid": ["resident_001", "tourist_001", "short_term_001"],
                "visitortype": ["Resident", "Tourist", "ShortTermVisitor"],
            }
        )

        with patch(
            "etls.crowd.crowd_classification_etl.etl.create_or_update_crowd_visitors_batch"
        ) as mock_store:
            etl.load()

            # Should only store 2 visitors (not ShortTermVisitor)
            call_args = mock_store.call_args
            visitor_ids = call_args[0][1]
            visitor_types = call_args[0][3]

            assert len(visitor_ids) == 2
            assert "short_term_001" not in visitor_ids
            assert "ShortTermVisitor" not in visitor_types

    def test_load_passes_correct_data_to_batch_function(self, etl_with_classified_data):
        """Test that load passes correct data to create_or_update_crowd_visitors_batch."""
        etl = etl_with_classified_data
        etl.classified_visitors = pd.DataFrame(
            {
                "visitorid": ["visitor_001", "visitor_002"],
                "visitortype": ["Resident", "Tourist"],
            }
        )

        with patch(
            "etls.crowd.crowd_classification_etl.etl.create_or_update_crowd_visitors_batch"
        ) as mock_store:
            etl.load()

            call_args = mock_store.call_args
            # Args: (db, visitor_ids, user_id, visitor_types)
            assert call_args[0][0] == etl.main_db
            assert call_args[0][1] == ["visitor_001", "visitor_002"]
            assert call_args[0][2] == etl.user_id
            assert call_args[0][3] == ["Resident", "Tourist"]


    def test_load_chunks_large_datasets(self, etl_with_classified_data):
        """Test that load chunks large datasets correctly."""
        etl = etl_with_classified_data
        # Create data larger than default chunk size (5000)
        num_visitors = 12000
        etl.classified_visitors = pd.DataFrame(
            {
                "visitorid": [f"visitor_{i:05d}" for i in range(num_visitors)],
                "visitortype": ["Resident"] * num_visitors,
            }
        )

        with patch(
            "etls.crowd.crowd_classification_etl.etl.create_or_update_crowd_visitors_batch"
        ) as mock_store:
            etl.load()

            # Should be called 3 times: 5000 + 5000 + 2000
            assert mock_store.call_count == 3

# =======================================================================
# --- JOB TESTS ---
# =======================================================================


class TestCrowdClassificationAllJob:
    """Test suite for the CrowdClassificationAll job class."""

    def test_job_only_runs_on_wednesday(self, mock_main_db):
        """Test that jobs are only started on Wednesdays."""
        # Monday (weekday 0)
        request = AllCrowdClassificationRequest(
            start_date=datetime(2023, 1, 2, 10, 0, 0),  # Monday
            end_date=datetime(2023, 1, 9, 10, 0, 0),
        )

        sample_entities = [_create_entity(1, "sensor-01_CFE", "Sensor Alpha")]

        with patch("tasks.crowd.classification_job.delay") as mock_delay:
            job = CrowdClassificationAll(request=request, db=mock_main_db)
            result = job._CrowdClassificationAll__start_jobs(
                user_id=1, entities=sample_entities
            )

            # Should not create jobs on Monday
            assert result is None
            mock_delay.assert_not_called()

    def test_job_runs_on_wednesday(self, mock_main_db):
        """Test that jobs are started on Wednesdays."""
        # Wednesday (weekday 2)
        request = AllCrowdClassificationRequest(
            start_date=datetime(2023, 1, 4, 10, 0, 0),  # Wednesday
            end_date=datetime(2023, 1, 11, 10, 0, 0),
        )

        sample_entities = [_create_entity(1, "sensor-01_CFE", "Sensor Alpha")]

        with patch("tasks.crowd.classification_job.delay") as mock_delay:
            job = CrowdClassificationAll(request=request, db=mock_main_db)
            job._CrowdClassificationAll__start_jobs(
                user_id=1, entities=sample_entities
            )

            # Should create jobs on Wednesday
            assert mock_delay.call_count >= 1

    def test_job_normalizes_dates_to_day_start(self, mock_main_db):
        """Test that dates are normalized to day boundaries (hour=0, minute=0)."""
        # Wednesday
        request = AllCrowdClassificationRequest(
            start_date=datetime(2023, 1, 4, 10, 30, 45),  # Wednesday
            end_date=datetime(2023, 1, 11, 12, 45, 30),
        )

        sample_entities = [_create_entity(1, "sensor-01_CFE", "Sensor Alpha")]

        with patch("tasks.crowd.classification_job.delay") as mock_delay:
            job = CrowdClassificationAll(request=request, db=mock_main_db)
            job._CrowdClassificationAll__start_jobs(
                user_id=1, entities=sample_entities
            )

            # All delayed requests should have normalized dates
            for call_args in mock_delay.call_args_list:
                req = call_args[0][0]
                start_date = _get_datetime_from_request(req, "start_date")
                end_date = _get_datetime_from_request(req, "end_date")

                assert start_date.hour == 0
                assert start_date.minute == 0
                assert start_date.second == 0
                assert start_date.microsecond == 0
                assert end_date.hour == 0
                assert end_date.minute == 0
                assert end_date.second == 0
                assert end_date.microsecond == 0

    def test_job_creates_weekly_windows(self, mock_main_db):
        """Test that jobs are queued in 7-day windows."""
        # Wednesday to 3 weeks later
        request = AllCrowdClassificationRequest(
            start_date=datetime(2023, 1, 4, 0, 0, 0),  # Wednesday
            end_date=datetime(2023, 1, 25, 0, 0, 0),  # 3 weeks later
        )

        sample_entities = [_create_entity(1, "sensor-01_CFE", "Sensor Alpha")]

        with patch("tasks.crowd.classification_job.delay") as mock_delay:
            job = CrowdClassificationAll(request=request, db=mock_main_db)
            job._CrowdClassificationAll__start_jobs(
                user_id=1, entities=sample_entities
            )

            # Should create 3 weekly windows: week 1, week 2, week 3
            assert mock_delay.call_count == 3

            # Verify window boundaries (7 days apart)
            expected_windows = [
                (datetime(2023, 1, 4, 0, 0), datetime(2023, 1, 11, 0, 0)),
                (datetime(2023, 1, 11, 0, 0), datetime(2023, 1, 18, 0, 0)),
                (datetime(2023, 1, 18, 0, 0), datetime(2023, 1, 25, 0, 0)),
            ]

            for i, call_args in enumerate(mock_delay.call_args_list):
                req = call_args[0][0]
                start_date = _get_datetime_from_request(req, "start_date")
                end_date = _get_datetime_from_request(req, "end_date")

                assert start_date == expected_windows[i][0]
                assert end_date == expected_windows[i][1]

    def test_job_sets_weekly_mode(self, mock_main_db):
        """Test that all queued jobs have weekly mode set."""
        # Wednesday
        request = AllCrowdClassificationRequest(
            start_date=datetime(2023, 1, 4, 0, 0, 0),  # Wednesday
            end_date=datetime(2023, 1, 11, 0, 0, 0),
        )

        sample_entities = [_create_entity(1, "sensor-01_CFE", "Sensor Alpha")]

        with patch("tasks.crowd.classification_job.delay") as mock_delay:
            job = CrowdClassificationAll(request=request, db=mock_main_db)
            job._CrowdClassificationAll__start_jobs(
                user_id=1, entities=sample_entities
            )

            for call_args in mock_delay.call_args_list:
                req = call_args[0][0]
                assert req.mode == "weekly"

    def test_job_returns_none_when_start_after_end(self, mock_main_db):
        """Test that job returns None when start_date > end_date."""
        # Wednesday
        request = AllCrowdClassificationRequest(
            start_date=datetime(2023, 1, 11, 0, 0, 0),  # Wednesday
            end_date=datetime(2023, 1, 4, 0, 0, 0),  # Before start
        )

        sample_entities = [_create_entity(1, "sensor-01_CFE", "Sensor Alpha")]

        with patch("tasks.crowd.classification_job.delay") as mock_delay:
            job = CrowdClassificationAll(request=request, db=mock_main_db)
            result = job._CrowdClassificationAll__start_jobs(
                user_id=1, entities=sample_entities
            )

            assert result is None
            mock_delay.assert_not_called()

    def test_job_passes_entities_to_request(self, mock_main_db):
        """Test that entities are correctly passed to each job request."""
        # Wednesday
        request = AllCrowdClassificationRequest(
            start_date=datetime(2023, 1, 4, 0, 0, 0),  # Wednesday
            end_date=datetime(2023, 1, 11, 0, 0, 0),
        )

        sample_entities = [
            _create_entity(1, "sensor-01_CFE", "Sensor Alpha"),
            _create_entity(2, "sensor-02_CFE", "Sensor Beta"),
        ]

        with patch("tasks.crowd.classification_job.delay") as mock_delay:
            job = CrowdClassificationAll(request=request, db=mock_main_db)
            job._CrowdClassificationAll__start_jobs(
                user_id=1, entities=sample_entities
            )

            assert mock_delay.call_count == 1
            req = mock_delay.call_args[0][0]

            assert len(req.entities) == 2

    def test_job_uses_default_dates_when_not_provided(self, mock_main_db):
        """Test that job uses default dates when start/end not provided."""
        request = AllCrowdClassificationRequest(
            start_date=None,
            end_date=None,
        )

        sample_entities = [_create_entity(1, "sensor-01_CFE", "Sensor Alpha")]

        with patch("tasks.crowd.classification_job.delay") as mock_delay:
            with patch(
                "jobs.crowd.all_crowd_classification_jobs.datetime"
            ) as mock_datetime:
                # Mock now as Wednesday
                mock_now = datetime(2023, 1, 4, 14, 30, 45)  # Wednesday
                mock_datetime.now.return_value = mock_now
                mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                    *args, **kwargs
                )

                job = CrowdClassificationAll(request=request, db=mock_main_db)
                job._CrowdClassificationAll__start_jobs(
                    user_id=1, entities=sample_entities
                )

                # Should have been called with default date range
                assert mock_delay.call_count >= 1
