import pytest
import pandas as pd
from unittest.mock import patch, MagicMock, call
from models.preferences_model import PreferenceType
from sqlalchemy.orm import Session
from datetime import datetime

# --- Schemas ---
from schemas.crowd_unique_visitors_request_schema import (
    AllCrowdUniqueVisitorsRequest,
    CrowdUniqueVisitorsRequest,
    CrowdUniqueVisitorsEntity,
)

# --- Classes Under Test ---
from etls.crowd.crowd_unique_visitors_etl.extract.crowd_unique_visitors_extract import UniqueVisitorsExtract
from etls.crowd.crowd_unique_visitors_etl.load.crowd_unique_visitors_load import UniqueVisitorsLoad
from etls.crowd.crowd_unique_visitors_etl.transform.crowd_unique_visitors_transform import UniqueVisitorsTransform
from jobs.crowd.all_crowd_unique_visitors_jobs import CrowdUniqueVisitorsAll

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

def _get_datetime_from_request(request_obj, attr_name="end_date"):
    """Helper to extract datetime from request, handling both datetime and ISO string."""
    value = getattr(request_obj, attr_name)
    return value if isinstance(value, datetime) else datetime.fromisoformat(value)

def _create_entity(entity_id, urn_suffix):
    """Factory function to create CrowdUniqueVisitorsEntity."""
    return CrowdUniqueVisitorsEntity(
        id=entity_id,
        urn=f"urn:ngsi-ld:CrowdFlowEvent:{urn_suffix}",
        tenant="pid",
        scope="/",
    )

def _filter_calls_by_mode(mock_delay, mode):
    """Helper to filter mock delay calls by aggregation mode."""
    return [
        call for call in mock_delay.call_args_list
        if call[0][0].aggregation_mode == mode
    ]

def _get_dates_from_calls(calls):
    """Extract end_date values from mock delay calls."""
    return [_get_datetime_from_request(call[0][0], "end_date") for call in calls]

@pytest.fixture
def sample_entities():
    """Provides sample entity data."""
    return [
        _create_entity(1, "Example1_CFE"),
        _create_entity(2, "Example2_CFE"),
    ]

@pytest.fixture
def base_request_params(sample_entities):
    """Provides base parameters for creating a request."""
    return {
        "entities": sample_entities,
        "end_date": datetime(2023, 1, 31, 10, 0, 0),
        "user_id": 1,
    }

@pytest.fixture
def sample_transform_data():
    """Provides sample DataFrame for transform testing."""
    entity1_urn = "urn:ngsi-ld:CrowdFlowEvent:Example1_CFE"
    entity2_urn = "urn:ngsi-ld:CrowdFlowEvent:Example2_CFE"

    return pd.DataFrame(
        {
            "entityid": [
                entity1_urn, entity1_urn, entity1_urn, entity1_urn, entity1_urn, entity1_urn,
                entity2_urn, entity2_urn, entity2_urn, entity2_urn,
            ],
            "visitorid": ["v10", "v1", "v2", "v1", "v3", "v10", "v4", "v1", "v4", "v4"],
            "timeinstant": [
                datetime(2023, 1, 7, 10, 0),
                datetime(2023, 1, 8, 10, 0),
                datetime(2023, 1, 8, 14, 0),
                datetime(2023, 1, 9, 8, 0),
                datetime(2023, 1, 16, 9, 0),
                datetime(2023, 2, 5, 10, 0),
                datetime(2023, 1, 8, 14, 0),
                datetime(2023, 1, 9, 10, 0),
                datetime(2023, 1, 9, 11, 0),
                datetime(2023, 2, 5, 11, 0),
            ],
        }
    )

@pytest.fixture
def sample_transform_output():
    """Provides sample transform output for load testing."""
    entity1_urn = "urn:ngsi-ld:CrowdFlowEvent:Example1_CFE"
    entity2_urn = "urn:ngsi-ld:CrowdFlowEvent:Example2_CFE"

    return {
        "result": pd.DataFrame(
            {
                "entityid": [entity1_urn, entity1_urn, entity2_urn],
                "unique_visitors": [1, 3, 2],
                "period_date": [
                    datetime(2023, 1, 9),
                    datetime(2023, 1, 10),
                    datetime(2023, 1, 10),
                ],
            }
        )
    }


class TestUniqueVisitorsETL:
    """
    Test suite for the CrowdUniqueVisitors ETL, focusing on
    extraction date logic, transform binning, and load payload generation.
    """

    @pytest.mark.parametrize(
        "mode, end_date, expected_start_date",
        [
            ("Daily", datetime(2023, 1, 10), datetime(2023, 1, 9)),
            ("Weekly", datetime(2023, 1, 10), datetime(2023, 1, 3)),
            ("Biweekly", datetime(2023, 1, 16), datetime(2023, 1, 2)),
            ("Monthly", datetime(2023, 1, 10), datetime(2022, 12, 10)),
        ],
    )
    def test_extract_get_period_start_from_end(
        self, base_request_params, mode, end_date, expected_start_date
    ):
        base_request_params["aggregation_mode"] = mode
        base_request_params["end_date"] = end_date
        request = CrowdUniqueVisitorsRequest(**base_request_params)

        extractor = UniqueVisitorsExtract(request, MagicMock(), MagicMock())

        calc_start = extractor.get_period_start_from_end(end_date)
        assert calc_start == expected_start_date

    @pytest.mark.parametrize(
    "aggregation_mode, start_date, end_date, time_bins_mock, expected_data",
    [
        (
            "Daily",
            datetime(2023, 1, 8),
            datetime(2023, 1, 10),
            [datetime(2023, 1, 8), datetime(2023, 1, 9), datetime(2023, 1, 10)],
            {
                "entityid": [
                    "urn:ngsi-ld:CrowdFlowEvent:Example1_CFE",
                    "urn:ngsi-ld:CrowdFlowEvent:Example2_CFE",
                    "urn:ngsi-ld:CrowdFlowEvent:Example1_CFE",
                    "urn:ngsi-ld:CrowdFlowEvent:Example2_CFE",
                ],
                "unique_visitors": [2, 1, 1, 2],
                "period_date": [
                    datetime(2023, 1, 9),
                    datetime(2023, 1, 9),
                    datetime(2023, 1, 10),
                    datetime(2023, 1, 10),
                ],
            }
        ),
        (
            "Weekly",
            datetime(2023, 1, 7),
            datetime(2023, 2, 6),
            [datetime(2023, 1, 7), datetime(2023, 1, 14), datetime(2023, 1, 21), datetime(2023, 2, 6)],
            {
                "entityid": [
                    "urn:ngsi-ld:CrowdFlowEvent:Example1_CFE",
                    "urn:ngsi-ld:CrowdFlowEvent:Example1_CFE",
                    "urn:ngsi-ld:CrowdFlowEvent:Example1_CFE",
                    "urn:ngsi-ld:CrowdFlowEvent:Example2_CFE",
                    "urn:ngsi-ld:CrowdFlowEvent:Example2_CFE",  # Bin 2: no data -> 0
                    "urn:ngsi-ld:CrowdFlowEvent:Example2_CFE",
                ],
                "unique_visitors": [3, 1, 1, 2, 0, 1],
                "period_date": [
                    datetime(2023, 1, 14),
                    datetime(2023, 1, 21),
                    datetime(2023, 2, 6),
                    datetime(2023, 1, 14),
                    datetime(2023, 1, 21),
                    datetime(2023, 2, 6),
                ],
            }
        ),
        (
            "Monthly",
            datetime(2023, 1, 1),
            datetime(2023, 3, 1),
            [datetime(2023, 1, 1), datetime(2023, 2, 1), datetime(2023, 3, 1)],
            {
                "entityid": [
                    "urn:ngsi-ld:CrowdFlowEvent:Example1_CFE",
                    "urn:ngsi-ld:CrowdFlowEvent:Example1_CFE",
                    "urn:ngsi-ld:CrowdFlowEvent:Example2_CFE",
                    "urn:ngsi-ld:CrowdFlowEvent:Example2_CFE",
                ],
                "unique_visitors": [4, 1, 2, 1],
                "period_date": [
                    datetime(2023, 2, 1),
                    datetime(2023, 3, 1),
                    datetime(2023, 2, 1),
                    datetime(2023, 3, 1),
                ],
            }
        ),
    ]
)
    
    def test_transform_aggregation_modes(
        self,
        base_request_params,
        sample_transform_data,
        aggregation_mode,
        start_date,
        end_date,
        time_bins_mock,
        expected_data
    ):
        base_request_params["aggregation_mode"] = aggregation_mode
        base_request_params["end_date"] = end_date
        request = CrowdUniqueVisitorsRequest(**base_request_params)

        extract_output = {
            "df_raw": sample_transform_data,
            "start_date": start_date,
            "end_date": end_date,
        }

        transformer = UniqueVisitorsTransform(
            request=request,
            extract_output=extract_output,
            main_db=MagicMock(),
            realtime_db=MagicMock(),
        )

        transformer._generate_relative_time_bins = MagicMock(
            return_value=time_bins_mock
        )

        result_df = transformer.transform()["result"]
        expected_df = pd.DataFrame(expected_data)

        result_df_sorted = result_df.sort_values(
            by=["entityid", "period_date"]
        ).reset_index(drop=True)
        expected_df_sorted = expected_df.sort_values(
            by=["entityid", "period_date"]
        ).reset_index(drop=True)

        result_df_sorted['period_date'] = pd.to_datetime(result_df_sorted['period_date'])

        pd.testing.assert_frame_equal(result_df_sorted, expected_df_sorted)


    @pytest.mark.parametrize(
        "mode, expected_attr_name",
        [
            ("Daily", "uniqueVisitorsDaily"),
            ("Weekly", "uniqueVisitorsWeekly"),
            ("Biweekly", "uniqueVisitorsBiweekly"),
            ("Monthly", "uniqueVisitorsMonthly"),
        ],
    )
    def test_load_generate_entity_payload_and_process(
        self,
        base_request_params,
        sample_transform_output,
        mode,
        expected_attr_name,
        mock_main_db,
        mock_realtime_db,
    ):
        base_request_params["aggregation_mode"] = mode
        base_request_params["end_date"] = datetime(2023, 1, 31)

        request = CrowdUniqueVisitorsRequest(**base_request_params)

        # Add new_visitor_counts to transform output
        transform_output_with_counts = sample_transform_output.copy()
        transform_output_with_counts["new_visitor_counts"] = {}

        loader = UniqueVisitorsLoad(
            request=request,
            transform_output=transform_output_with_counts,
            main_db=mock_main_db,
            realtime_db=mock_realtime_db,
        )

        payload = loader.process_to_fiware(sample_transform_output["result"])

        assert len(payload) == 3

        payload.sort(key=lambda x: (x["entityId"], x["TimeInstant"]))

        data0 = payload[0]
        assert data0["entityId"] == "Example1_CFE"
        assert expected_attr_name in data0
        assert data0[expected_attr_name] == 1
        assert data0["TimeInstant"] == "2023-01-09T00:00:00"
        assert data0["endDate"] == "2023-01-09T00:00:00"

        if mode == "Daily":
            assert data0["startDate"] == "2023-01-08T00:00:00"
        elif mode == "Weekly":
            assert data0["startDate"] == "2023-01-02T00:00:00"
        elif mode == "Biweekly":
            assert data0["startDate"] == "2022-12-26T00:00:00"
        elif mode == "Monthly":
            assert data0["startDate"] == "2022-12-09T00:00:00"

        data1 = payload[1]
        assert data1["entityId"] == "Example1_CFE"
        assert expected_attr_name in data1
        assert data1[expected_attr_name] == 3
        assert data1["TimeInstant"] == "2023-01-10T00:00:00"
        assert data1["endDate"] == "2023-01-10T00:00:00"

        if mode == "Daily":
            assert data1["startDate"] == "2023-01-09T00:00:00"
        elif mode == "Weekly":
            assert data1["startDate"] == "2023-01-03T00:00:00"
        elif mode == "Biweekly":
            assert data1["startDate"] == "2022-12-27T00:00:00"
        elif mode == "Monthly":
            assert data1["startDate"] == "2022-12-10T00:00:00"

        data2 = payload[2]
        assert data2["entityId"] == "Example2_CFE"
        assert expected_attr_name in data2
        assert data2[expected_attr_name] == 2
        assert data2["TimeInstant"] == "2023-01-10T00:00:00"
        assert data2["endDate"] == "2023-01-10T00:00:00"

        if mode == "Daily":
            assert data2["startDate"] == "2023-01-09T00:00:00"
        elif mode == "Weekly":
            assert data2["startDate"] == "2023-01-03T00:00:00"
        elif mode == "Biweekly":
            assert data2["startDate"] == "2022-12-27T00:00:00"
        elif mode == "Monthly":
            assert data2["startDate"] == "2022-12-10T00:00:00"


    def test_load_empty_dataframe(
        self,
        base_request_params,
        mock_main_db,
        mock_realtime_db,
    ):
        empty_transform_output = {
            "result": pd.DataFrame(),
            "new_visitor_counts": {}
        }

        request = CrowdUniqueVisitorsRequest(**base_request_params)

        loader = UniqueVisitorsLoad(
            request=request,
            transform_output=empty_transform_output,
            main_db=mock_main_db,
            realtime_db=mock_realtime_db,
        )

        with patch(
            "etls.crowd.crowd_unique_visitors_etl.load.crowd_unique_visitors_load.UniqueVisitorsLoad.send_to_iota"
        ) as mock_send_to_iota:

            loader.load()
            mock_send_to_iota.assert_not_called()

    @pytest.mark.parametrize(
        "mode",
        ["Weekly", "Biweekly", "Monthly"],
    )
    def test_load_new_visitor_counts_with_period_suffix(
        self,
        base_request_params,
        sample_transform_output,
        mode,
        mock_main_db,
        mock_realtime_db,
    ):
        """Test that new visitor counts are included in payload with period suffix for non-Daily modes."""
        base_request_params["aggregation_mode"] = mode
        base_request_params["end_date"] = datetime(2023, 1, 31)

        request = CrowdUniqueVisitorsRequest(**base_request_params)

        # Add new_visitor_counts to transform output
        transform_output_with_counts = sample_transform_output.copy()
        transform_output_with_counts["new_visitor_counts"] = {
            'newUniqueVisitors': 10,
            'newResidentUniqueVisitors': 6,
            'newTouristUniqueVisitors': 4
        }

        loader = UniqueVisitorsLoad(
            request=request,
            transform_output=transform_output_with_counts,
            main_db=mock_main_db,
            realtime_db=mock_realtime_db,
        )

        payload = loader.process_to_fiware(sample_transform_output["result"])

        # Check that all payload items contain the new visitor counts
        for item in payload:
            assert f"newUniqueVisitors{mode}" in item
            assert f"newResidentUniqueVisitors{mode}" in item
            assert f"newTouristUniqueVisitors{mode}" in item

            assert item[f"newUniqueVisitors{mode}"] == 10
            assert item[f"newResidentUniqueVisitors{mode}"] == 6
            assert item[f"newTouristUniqueVisitors{mode}"] == 4

    def test_load_daily_mode_no_new_visitor_counts(
        self,
        base_request_params,
        sample_transform_output,
        mock_main_db,
        mock_realtime_db,
    ):
        """Test that Daily mode does not compute new visitor counts."""
        base_request_params["aggregation_mode"] = "Daily"
        base_request_params["end_date"] = datetime(2023, 1, 31)

        request = CrowdUniqueVisitorsRequest(**base_request_params)

        # Daily mode should have empty new_visitor_counts
        transform_output_with_counts = sample_transform_output.copy()
        transform_output_with_counts["new_visitor_counts"] = {}

        loader = UniqueVisitorsLoad(
            request=request,
            transform_output=transform_output_with_counts,
            main_db=mock_main_db,
            realtime_db=mock_realtime_db,
        )

        payload = loader.process_to_fiware(sample_transform_output["result"])

        # Check that all new visitor counts are 0 (default)
        for item in payload:
            assert item["newUniqueVisitorsDaily"] == 0
            assert item["newResidentUniqueVisitorsDaily"] == 0
            assert item["newTouristUniqueVisitorsDaily"] == 0

    @pytest.mark.parametrize(
        "mode",
        ["Weekly", "Biweekly", "Monthly"],
    )
    def test_transform_new_visitor_calculation_logic(
        self,
        base_request_params,
        sample_transform_data,
        mode,
        mock_main_db,
        mock_realtime_db,
    ):
        """Test the actual calculation logic of new visitor counts in transform phase."""
        base_request_params["aggregation_mode"] = mode
        base_request_params["end_date"] = datetime(2023, 2, 6)
        request = CrowdUniqueVisitorsRequest(**base_request_params)

        start_date = datetime(2023, 1, 7)
        extract_output = {
            "df_raw": sample_transform_data,
            "start_date": start_date,
            "end_date": datetime(2023, 2, 6),
        }

        # Mock previous visitors from DB
        mock_previous_visitor = MagicMock()
        mock_previous_visitor.visitor_id = "v1"
        mock_previous_visitor.visitor_type = "Resident"

        # Mock created visitors (created_at >= start_date)
        # v10 is a new visitor created in this period
        mock_created_visitor = MagicMock()
        mock_created_visitor.visitor_id = "v10"

        # Mock updated visitors (updated_at >= start_date)
        # v2 was updated in this period (e.g., reclassified from Tourist to Resident)
        # v3 is a new resident
        mock_updated_visitor_v2 = MagicMock()
        mock_updated_visitor_v2.visitor_id = "v2"

        mock_updated_visitor_v3 = MagicMock()
        mock_updated_visitor_v3.visitor_id = "v3"

        mock_updated_visitor_v10 = MagicMock()
        mock_updated_visitor_v10.visitor_id = "v10"

        # Mock classified visitors DataFrame
        mock_classified_df = pd.DataFrame({
            'visitorid': ['v1', 'v2', 'v3', 'v10', 'v4'],
            'visitortype': ['Resident', 'Resident', 'Resident', 'Tourist', 'Tourist']
        })

        with patch('etls.crowd.crowd_unique_visitors_etl.transform.crowd_unique_visitors_transform.get_user_crowd_visitor') as mock_get_visitors, \
             patch('etls.crowd.crowd_unique_visitors_etl.transform.crowd_unique_visitors_transform.get_user_crowd_visitors_created_at') as mock_get_created, \
             patch('etls.crowd.crowd_unique_visitors_etl.transform.crowd_unique_visitors_transform.get_user_crowd_visitors_updated_at') as mock_get_updated, \
             patch('etls.crowd.crowd_unique_visitors_etl.transform.crowd_unique_visitors_transform.classify_visitors') as mock_classify:

            mock_get_visitors.return_value = [mock_previous_visitor]
            mock_get_created.return_value = [mock_created_visitor]
            mock_get_updated.return_value = [mock_updated_visitor_v2, mock_updated_visitor_v3, mock_updated_visitor_v10]
            mock_classify.return_value = mock_classified_df

            transformer = UniqueVisitorsTransform(
                request=request,
                extract_output=extract_output,
                main_db=mock_main_db,
                realtime_db=mock_realtime_db,
            )

            result = transformer.transform()
            new_visitor_counts = result["new_visitor_counts"]

            # Verify the calculation logic:
            # newUniqueVisitors: Only v10 (created_at >= start_date)
            assert new_visitor_counts['newUniqueVisitors'] == 1

            # newResidentUniqueVisitors: v2 (updated), v3 (updated & not in DB previously)
            # v1 is not new (was already in DB and not updated)
            assert new_visitor_counts['newResidentUniqueVisitors'] == 2

            # newTouristUniqueVisitors: v10 (updated & not in DB), v4 (not in DB)
            assert new_visitor_counts['newTouristUniqueVisitors'] == 2

    def test_transform_new_visitor_reclassification_scenario(
        self,
        base_request_params,
        mock_main_db,
        mock_realtime_db,
    ):
        """Test that a visitor reclassified from Tourist to Resident counts as new resident but not new visitor."""
        base_request_params["aggregation_mode"] = "Monthly"
        base_request_params["end_date"] = datetime(2023, 2, 1)
        request = CrowdUniqueVisitorsRequest(**base_request_params)

        # Raw data with visitor v100 who was previously a Tourist
        raw_data = pd.DataFrame({
            "entityid": ["urn:ngsi-ld:CrowdFlowEvent:Entity_CFE"] * 3,
            "visitorid": ["v100", "v100", "v200"],
            "timeinstant": [
                datetime(2023, 1, 15, 10, 0),
                datetime(2023, 1, 16, 10, 0),
                datetime(2023, 1, 17, 10, 0),
            ],
        })

        start_date = datetime(2023, 1, 1)
        extract_output = {
            "df_raw": raw_data,
            "start_date": start_date,
            "end_date": datetime(2023, 2, 1),
        }

        # v100 was previously a Tourist (in DB before start_date)
        mock_previous_v100 = MagicMock()
        mock_previous_v100.visitor_id = "v100"
        mock_previous_v100.visitor_type = "Tourist"

        # v100 was updated in this period (reclassified to Resident)
        mock_updated_v100 = MagicMock()
        mock_updated_v100.visitor_id = "v100"

        # No visitors were created in this period (v100 existed before, v200 is new but not in created list for testing)
        # v200 is truly new
        mock_created_v200 = MagicMock()
        mock_created_v200.visitor_id = "v200"

        # Classified visitors: v100 is now Resident, v200 is Tourist
        mock_classified_df = pd.DataFrame({
            'visitorid': ['v100', 'v200'],
            'visitortype': ['Resident', 'Tourist']
        })

        with patch('etls.crowd.crowd_unique_visitors_etl.transform.crowd_unique_visitors_transform.get_user_crowd_visitor') as mock_get_visitors, \
             patch('etls.crowd.crowd_unique_visitors_etl.transform.crowd_unique_visitors_transform.get_user_crowd_visitors_created_at') as mock_get_created, \
             patch('etls.crowd.crowd_unique_visitors_etl.transform.crowd_unique_visitors_transform.get_user_crowd_visitors_updated_at') as mock_get_updated, \
             patch('etls.crowd.crowd_unique_visitors_etl.transform.crowd_unique_visitors_transform.classify_visitors') as mock_classify:

            mock_get_visitors.return_value = [mock_previous_v100]
            mock_get_created.return_value = [mock_created_v200]
            mock_get_updated.return_value = [mock_updated_v100]
            mock_classify.return_value = mock_classified_df

            transformer = UniqueVisitorsTransform(
                request=request,
                extract_output=extract_output,
                main_db=mock_main_db,
                realtime_db=mock_realtime_db,
            )

            result = transformer.transform()
            new_visitor_counts = result["new_visitor_counts"]

            # v200 is the only truly new visitor (created in this period)
            assert new_visitor_counts['newUniqueVisitors'] == 1

            # v100 is a "new resident" (was updated - reclassified from Tourist to Resident)
            assert new_visitor_counts['newResidentUniqueVisitors'] == 1

            # v200 is not in DB, so counts as new tourist
            assert new_visitor_counts['newTouristUniqueVisitors'] == 1


class TestCrowdUniqueVisitorsAll: 

    def test_date_validation(self, sample_entities, mock_main_db):
        valid_request = AllCrowdUniqueVisitorsRequest(
            start_date=datetime(2023, 1, 1, 15, 30, 45),
            end_date=datetime(2023, 1, 3, 10, 20, 30),
        )

        with patch("tasks.crowd.unique_visitors_job.delay") as mock_delay:
            job = CrowdUniqueVisitorsAll(request=valid_request, db=mock_main_db)
            job.start_jobs(user_id=1, entities=sample_entities)

            for call_args in mock_delay.call_args_list:
                request = call_args[0][0]
                end_date = _get_datetime_from_request(request, "end_date")
                assert end_date.hour == 0
                assert end_date.minute == 0
                assert end_date.second == 0
                assert end_date.microsecond == 0

        invalid_request = AllCrowdUniqueVisitorsRequest(
            start_date=datetime(2023, 1, 10),
            end_date=datetime(2023, 1, 5),
        )

        with patch("tasks.crowd.unique_visitors_job.delay") as mock_delay:
            job = CrowdUniqueVisitorsAll(request=invalid_request, db=mock_main_db)
            result = job.start_jobs(user_id=1, entities=sample_entities)

            assert result is None
            mock_delay.assert_not_called()

    def test_job_queueing_logic(self, sample_entities, mock_main_db):
        request = AllCrowdUniqueVisitorsRequest(
            start_date=datetime(2021, 2, 28),
            end_date=datetime(2021, 3, 17),
        )

        with patch("tasks.crowd.unique_visitors_job.delay") as mock_delay:
            job = CrowdUniqueVisitorsAll(request=request, db=mock_main_db)
            job.start_jobs(user_id=1, entities=sample_entities)

            daily_calls = _filter_calls_by_mode(mock_delay, "Daily")
            assert len(daily_calls) == 17

            expected_daily_dates = [datetime(2021, 3, day) for day in range(1, 18)]
            actual_daily_dates = _get_dates_from_calls(daily_calls)
            assert actual_daily_dates == expected_daily_dates

            weekly_calls = _filter_calls_by_mode(mock_delay, "Weekly")
            assert len(weekly_calls) == 3

            weekly_dates = _get_dates_from_calls(weekly_calls)
            for date in weekly_dates:
                assert date.weekday() == 0

            assert datetime(2021, 3, 1) in weekly_dates
            assert datetime(2021, 3, 8) in weekly_dates
            assert datetime(2021, 3, 15) in weekly_dates

            biweekly_calls = _filter_calls_by_mode(mock_delay, "Biweekly")
            assert len(biweekly_calls) == 2

            biweekly_dates = _get_dates_from_calls(biweekly_calls)
            assert datetime(2021, 3, 1) in biweekly_dates
            assert datetime(2021, 3, 16) in biweekly_dates

            monthly_calls = _filter_calls_by_mode(mock_delay, "Monthly")
            assert len(monthly_calls) == 1

            monthly_date = _get_datetime_from_request(monthly_calls[0][0][0], "end_date")
            assert monthly_date == datetime(2021, 3, 1)
            assert monthly_date.day == 1

            # Test March 1st (should have Daily, Weekly, Biweekly, Monthly)
            march_1_calls = [
                call for call in mock_delay.call_args_list
                if _get_datetime_from_request(call[0][0], "end_date") == datetime(2021, 3, 1)
            ]

            assert len(march_1_calls) == 4

            aggregation_modes = {call[0][0].aggregation_mode for call in march_1_calls}
            assert aggregation_modes == {"Daily", "Weekly", "Biweekly", "Monthly"}

            # Test March 8th (should have Daily, Weekly)
            march_8_calls = [
                call for call in mock_delay.call_args_list
                if _get_datetime_from_request(call[0][0], "end_date") == datetime(2021, 3, 8)
            ]

            assert len(march_8_calls) == 2

            march_8_modes = {call[0][0].aggregation_mode for call in march_8_calls}
            assert march_8_modes == {"Daily", "Weekly"}

            # Test March 16th (should have Daily, Biweekly)
            march_16_calls = [
                call for call in mock_delay.call_args_list
                if _get_datetime_from_request(call[0][0], "end_date") == datetime(2021, 3, 16)
            ]

            assert len(march_16_calls) == 2

            march_16_modes = {call[0][0].aggregation_mode for call in march_16_calls}
            assert march_16_modes == {"Daily", "Biweekly"}

            # Test March 5th (should have Daily only)
            march_5_calls = [
                call for call in mock_delay.call_args_list
                if _get_datetime_from_request(call[0][0], "end_date") == datetime(2021, 3, 5)
            ]

            assert len(march_5_calls) == 1
            assert march_5_calls[0][0][0].aggregation_mode == "Daily"

    def test_start_jobs_default_dates(self, sample_entities, mock_main_db):
        request = AllCrowdUniqueVisitorsRequest(
            start_date=None,
            end_date=None
        )

        with patch("tasks.crowd.unique_visitors_job.delay") as mock_delay:
            with patch("jobs.crowd.all_crowd_unique_visitors_jobs.datetime") as mock_datetime:
                mock_now = datetime(2023, 1, 15, 14, 30, 45)
                mock_datetime.now.return_value = mock_now
                mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

                job = CrowdUniqueVisitorsAll(request=request, db=mock_main_db)
                job.start_jobs(user_id=1, entities=sample_entities)

                assert mock_delay.call_count >= 1

                last_call = mock_delay.call_args_list[-1]
                end_date = _get_datetime_from_request(last_call[0][0], "end_date")
                expected_end_date = datetime(2023, 1, 15, 0, 0, 0)
                assert end_date == expected_end_date