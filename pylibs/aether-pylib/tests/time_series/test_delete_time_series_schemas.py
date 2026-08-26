from datetime import datetime, timedelta
from typing import Tuple
import pytest
import freezegun

from aether_pylib.time_series.deleted_time_series import DeletedTimeSeries
from aether_pylib.time_series.delete_time_series_options import (
    DeleteTimeSeriesOptions,
)
from aether_pylib.time_series.delete_time_series_request import (
    DeleteTimeSeriesRequest,
)
from aether_pylib.time_series.delete_time_series_response import (
    DeleteTimeSeriesResponse,
)


# Reference time for freezegun to test relative durations
def reference_time() -> str:
    return "2022-07-01T00:00:00Z"


# Helper function for duration strings and their expected timedelta in seconds
def duration_string_with_reference_seconds() -> Tuple[str, int]:
    return [
        ("PT1M", 60),
        ("PT2H", 2 * 60 * 60),
        ("PT3H30M", 3 * 60 * 60 + 30 * 60),
        ("P1D", 24 * 60 * 60),
        ("P1DT1H", 24 * 60 * 60 + 3600),
        ("P1DT1H1M", 24 * 60 * 60 + 60 * 60 + 60),
        ("P1DT1H1M1S", 24 * 60 * 60 + 60 * 60 + 60 + 1),
        ("P1Y", 365 * 24 * 60 * 60),  # Assuming non-leap year for simplicity
        ("P1Y1M", (365 + 30) * 24 * 60 * 60),  # Assuming 30 days for a month
        ("P1Y1M1D", (365 + 30 + 1) * 24 * 60 * 60),
        ("P1Y1M1DT1H", (365 + 30 + 1) * 24 * 60 * 60 + 60 * 60),
        ("P1Y1M1DT1H1M", (365 + 30 + 1) * 24 * 60 * 60 + 60 * 60 + 60),
        ("P1Y1M1DT1H1M1S", (365 + 30 + 1) * 24 * 60 * 60 + 60 * 60 + 60 + 1),
    ]


class TestDeleteTimeSeriesSchemas:

    def test_deleted_time_series_instantiation(self):
        """Test basic instantiation of DeletedTimeSeries."""
        data = {
            "device_id": "urn:ngsi-ld:Building:001",
            "measure_id": "urn:ngsi-ld:Building:001:temperature",
        }
        deleted_ts = DeletedTimeSeries(**data)
        assert deleted_ts.device_id == "urn:ngsi-ld:Building:001"
        assert deleted_ts.measure_id == "urn:ngsi-ld:Building:001:temperature"

    @pytest.mark.parametrize(
        ("date_param", "date_value", "valid"),
        [
            (date_param, test_value[0], test_value[1])
            for date_param in ["start_date", "end_date"]
            for test_value in [
                # valid absolute dates
                ("2020-01-01T00:00:00Z", True),
                ("2990-01-01T00:00:00Z", True),
                ("2020-01-01T00:00:00", True),
                ("2020-01-01T00:00:00+00:00", True),
                ("2020-01-01T00:00:00+03:00", True),
                # valid duration strings
                ("PT1H", True),
                ("PT1H30M", True),
                ("PT1H30M30S", True),
                ("P1Y", True),
                ("P1Y1M", True),
                ("P1Y1M1D", True),
                ("P1Y1M1DT1H", True),
                ("P1Y1M1DT1H1M", True),
                ("P1Y1M1DT1H1M1S", True),
                # invalid date formats
                ("", False),
                ("2020-01-01", False),  # no time
                ("2020-01-01T00:00:00+3:00", False),  # timezone (wrong format)
                ("PW", False),  # invalid duration
            ]
        ],
    )
    def test_date_in_delete_time_series_options(
        self, date_param: str, date_value: str, valid: bool
    ):
        """Test date parsing and validation in DeleteTimeSeriesOptions."""
        try:
            DeleteTimeSeriesOptions(
                **{date_param: date_value, "tenant": "test_tenant", "scope": "/"}
            )
            assert valid
        except Exception as e:
            assert (
                not valid
            ), f"Validation failed unexpectedly for {date_param}: {date_value} with error: {e}"

    @pytest.mark.parametrize(
        ("date_param", "date_duration_value", "expected_timedelta_in_seconds"),
        [
            (date_param, test_value[0], test_value[1])
            for date_param in ["start_date", "end_date"]
            for test_value in duration_string_with_reference_seconds()
        ],
    )
    @freezegun.freeze_time(reference_time())
    def test_relative_date_in_delete_time_series_options(
        self,
        date_param: str,
        date_duration_value: str,
        expected_timedelta_in_seconds: int,
    ):
        """Test relative date parsing in DeleteTimeSeriesOptions."""
        # The validator replaces tzinfo with None, so we compare without timezone
        expected_date = (
            datetime.now() - timedelta(seconds=expected_timedelta_in_seconds)
        ).replace(tzinfo=None)

        options = DeleteTimeSeriesOptions(
            **{date_param: date_duration_value, "tenant": "test_tenant", "scope": "/"}
        )
        # Access the parsed datetime object from the model's data
        assert expected_date == options.model_dump()[date_param]

    def test_delete_time_series_options_optional_fields(self):
        """Test instantiation of DeleteTimeSeriesOptions with only required fields."""
        options = DeleteTimeSeriesOptions(tenant="test_tenant", scope="/")
        assert options.tenant == "test_tenant"
        assert options.scope == "/"
        assert options.start_date is None
        assert options.end_date is None
        assert options.query_id is None

    @pytest.mark.parametrize(
        ("params", "valid"),
        [
            (
                {
                    "device_ids": ["urn:ngsi-ld:Building:001"],
                    "measure_ids": ["temperature"],
                    "options": {
                        "start_date": "2020-01-01T00:00:00Z",
                        "end_date": "2020-01-01T00:03:00Z",
                        "query_id": "123",
                        "tenant": "gijon",
                        "scope": "/",
                    },
                },
                True,
            ),
            (
                {
                    "device_ids": [
                        "urn:ngsi-ld:Building:001",
                        "urn:ngsi-ld:Building:002",
                    ],
                    "measure_ids": ["temperature", "humidity"],
                    "options": {
                        "tenant": "gijon",
                        "scope": "/",
                    },
                },
                True,
            ),
            (
                {
                    "device_ids": [],
                    "measure_ids": ["temperature"],
                    "options": {
                        "tenant": "gijon",
                        "scope": "/",
                    },
                },
                False,  # device_ids cannot be empty
            ),
            (
                {
                    "device_ids": ["urn:ngsi-ld:Building:001"],
                    "measure_ids": [],  # measure_ids can be empty
                    "options": {
                        "tenant": "gijon",
                        "scope": "/",
                    },
                },
                True,
            ),
        ],
    )
    def test_delete_time_series_request_validation(self, params: dict, valid: bool):
        """Test validation rules for DeleteTimeSeriesRequest."""
        try:
            DeleteTimeSeriesRequest(**params)
            assert valid
        except Exception as e:
            assert (
                not valid
            ), f"Validation failed unexpectedly for params: {params} with error: {e}"

    def test_delete_time_series_response_instantiation(self):
        """Test basic instantiation of DeleteTimeSeriesResponse."""
        data = {
            "deleted_time_series": [
                {
                    "device_id": "urn:ngsi-ld:Building:001",
                    "measure_id": "urn:ngsi-ld:Building:001:temperature",
                }
            ],
            "options": {
                "start_date": "2020-01-01T00:00:00Z",
                "end_date": "2020-01-01T00:03:00Z",
                "query_id": "123",
                "tenant": "gijon",
                "scope": "/",
            },
        }
        response = DeleteTimeSeriesResponse(**data)
        assert len(response.deleted_time_series) == 1
        assert response.deleted_time_series[0].device_id == "urn:ngsi-ld:Building:001"
        assert response.options.tenant == "gijon"
