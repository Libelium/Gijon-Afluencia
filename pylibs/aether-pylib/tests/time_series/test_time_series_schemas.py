from datetime import datetime, timedelta
from typing import Tuple
from aether_pylib.time_series.time_series_options import (
    TimeSeriesAggregationOptions,
    TimeSeriesOptions,
)
from aether_pylib.time_series.time_series_request import TimeSeriesRequest
import pytest
import freezegun


# it should be a leap year to avoid problems
def reference_time() -> str:
    return "2022-07-01T00:00:00Z"


def duarion_string_with_reference_seconds_unitl_month() -> Tuple[str, int]:
    return [
        ("PT1M", 60),
        ("PT2H", 2 * 60 * 60),
        ("PT3H30M", 3 * 60 * 60 + 30 * 60),
        ("P1D", 24 * 60 * 60),
        ("P1DT1H", 24 * 60 * 60 + 3600),
        ("P1DT1H1M", 24 * 60 * 60 + 60 * 60 + 60),
    ]


def duration_string_with_reference_seconds() -> Tuple[str, int]:
    return [
        *duarion_string_with_reference_seconds_unitl_month(),
        ("P1DT1H1M1S", 24 * 60 * 60 + 60 * 60 + 60 + 1),
        ("P1Y", 365 * 24 * 60 * 60),
        ("P1Y1M", 365 * 24 * 60 * 60 + 30 * 24 * 60 * 60),
        ("P1Y1M1D", 365 * 24 * 60 * 60 + 30 * 24 * 60 * 60 + 24 * 60 * 60),
        (
            "P1Y1M1DT1H",
            365 * 24 * 60 * 60 + 30 * 24 * 60 * 60 + 24 * 60 * 60 + 60 * 60,
        ),
        (
            "P1Y1M1DT1H1M",
            365 * 24 * 60 * 60 + 30 * 24 * 60 * 60 + 24 * 60 * 60 + 60 * 60 + 60,
        ),
        (
            "P1Y1M1DT1H1M1S",
            365 * 24 * 60 * 60 + 30 * 24 * 60 * 60 + 24 * 60 * 60 + 60 * 60 + 60 + 1,
        ),
    ]


class TestTimeSeriesOptions:
    @pytest.mark.parametrize(
        ("date_param", "date_value", "valid"),
        [
            (date_param, test_value[0], test_value[1])
            for date_param in ["start_date", "end_date"]
            for test_value in [
                # valid
                ("2020-01-01T00:00:00Z", True),  # simple
                ("2990-01-01T00:00:00Z", True),  # far future
                ("2020-01-01T00:00:00", True),  # no timezone
                ("2020-01-01T00:00:00+00:00", True),  # timezone
                ("2020-01-01T00:00:00+03:00", True),  # timezone (different)
                ("PT1H", True),  # duration
                ("PT1H30M", True),  # duration
                ("PT1H30M30S", True),  # duration
                ("P1Y", True),  # duration"
                ("P1Y1M", True),  # duration"
                ("P1Y1M1D", True),  # duration"
                ("P1Y1M1DT1H", True),  # duration"
                ("P1Y1M1DT1H1M", True),  # duration"
                ("P1Y1M1DT1H1M1S", True),  # duration"
                # invalid
                ("", False),  # empty
                ("2020-01-01", False),  # no time
                ("2020-01-01T00:00:00+3:00", False),  # timezone (wrong format)
                ("2020-01-01T00:00:00+03", False),  # timezone (wrong format)
                ("2020-01-01T00:00:00+3", False),  # timezone (wrong format)
                ("PW", False),  # duration"
                ("P1W1Y", False),  # duration"
                ("P1W1Y1M", False),  # duration"
                ("P1W1Y1M1D", False),  # duration"
            ]
        ],
    )
    def test_date_in_time_series_options(
        self, date_param: str, date_value: str, valid: bool
    ):
        try:
            TimeSeriesOptions(
                **{date_param: date_value, "tenant": "tenant", "scope": "scope"}
            )
            assert valid
        except Exception as e:
            assert not valid

    @pytest.mark.parametrize(
        ("date_param", "date_duration_value", "expected_timedelta_in_seconds"),
        [
            (date_param, test_value[0], test_value[1])
            for date_param in ["start_date", "end_date"]
            for test_value in duration_string_with_reference_seconds()
        ],
    )
    @freezegun.freeze_time(reference_time())
    def test_relative_date_in_time_series_options(
        self,
        date_param: str,
        date_duration_value: str,
        expected_timedelta_in_seconds: int,
    ):
        # compare ignoring timezone
        expected_date = datetime.now() - timedelta(
            seconds=expected_timedelta_in_seconds
        )

        options = TimeSeriesOptions(
            **{date_param: date_duration_value, "tenant": "tenant", "scope": "scope"}
        )

        assert expected_date == options.model_dump()[date_param]

    @pytest.mark.parametrize(
        ("date_duration_value", "expected_timedelta_in_seconds"),
        duarion_string_with_reference_seconds_unitl_month(),
    )
    @freezegun.freeze_time(reference_time())
    def test_duration_interval_in_time_series_aggregation_options(
        self, date_duration_value: str, expected_timedelta_in_seconds: int
    ):
        aggregation_options = TimeSeriesAggregationOptions(
            **{"type": "mean", "interval": date_duration_value}
        )

        expected_interval = timedelta(seconds=expected_timedelta_in_seconds)

        assert expected_interval == aggregation_options.interval

    @pytest.mark.parametrize(
        ("params"),
        [
            {
                "start_date": "2020-01-01T00:00:00Z",
                "end_date": "2020-01-01T00:00:00Z",
                "order": "asc",
                "limit": 100,
                "aggregation": {"type": "mean", "interval": "PT35S"},
                "tenant": "tenant",
                "scope": "scope",
            },
            {
                "end_date": "2020-01-01T00:00:00Z",
                "order": "asc",
                "limit": 100,
                "aggregation": {"type": "mean", "interval": "PT35S"},
                "tenant": "tenant",
                "scope": "scope",
            },
            {
                "start_date": "2020-01-01T00:00:00Z",
                "order": "asc",
                "limit": 100,
                "aggregation": {"type": "mean", "interval": "PT35S"},
                "tenant": "tenant",
                "scope": "scope",
            },
            {
                "start_date": "2020-01-01T00:00:00Z",
                "end_date": "2020-01-01T00:00:00Z",
                "limit": 100,
                "aggregation": {"type": "mean", "interval": "PT35S"},
                "tenant": "tenant",
                "scope": "scope",
            },
            {
                "start_date": "2020-01-01T00:00:00Z",
                "end_date": "2020-01-01T00:00:00Z",
                "order": "asc",
                "aggregation": {"type": "mean", "interval": "PT35S"},
                "tenant": "tenant",
                "scope": "scope",
            },
            {
                "start_date": "2020-01-01T00:00:00Z",
                "end_date": "2020-01-01T00:00:00Z",
                "order": "asc",
                "limit": 100,
                "tenant": "tenant",
                "scope": "scope",
            },
            {
                "start_date": "2020-01-01T00:00:00Z",
                "end_date": "2020-01-01T00:00:00Z",
                "order": "asc",
                "limit": 100,
                "aggregation": {"type": "mean", "interval": "PT35S"},
                "tenant": "tenant",
                "scope": "scope",
            },
        ],
    )
    def test_optional_fields_in_time_series_options(self, params: dict):
        options = TimeSeriesOptions(**params)
        assert True

    @pytest.mark.parametrize(
        ("params", "valid"),
        [
            (
                {
                    "device_ids": [],
                    "measure_ids": ["temperature"],
                    "options": {
                        "tenant": "tenant",
                        "scope": "scope",
                        "where": {
                            "conditions": [["field1", "=", 1]],
                            "operation": "AND",
                        },
                    },
                },
                True,
            ),
            (
                {
                    "device_ids": ["urn:ngsi-ld:Building:001"],
                    "measure_ids": ["temperature"],
                    "options": {
                        "tenant": "tenant",
                        "scope": "scope",
                        "where": {
                            "conditions": [["field1", "=", 1]],
                            "operation": "AND",
                        },
                    },
                },
                True,
            ),
            (
                {
                    "device_ids": ["urn:ngsi-ld:Building:001"],
                    "measure_ids": ["temperature"],
                    "options": {
                        "tenant": "tenant",
                        "scope": "scope",
                    },
                },
                True,
            ),
            (
                {
                    "device_ids": [],
                    "measure_ids": ["temperature"],
                    "options": {
                        "tenant": "tenant",
                        "scope": "scope",
                    },
                },
                False,
            ),
            # This test is false because we dont support multiple conditions yet,
            # and should be removed when we support it
            (
                {
                    "device_ids": ["urn:ngsi-ld:Building:001"],
                    "measure_ids": ["temperature"],
                    "options": {
                        "tenant": "tenant",
                        "scope": "scope",
                        "where": {
                            "conditions": [["field1", "=", 1], ["field2", "=", "2"]],
                            "operation": "AND",
                        },
                    },
                },
                False,
            ),
            # test timezone in TimeScope
            (
                {
                    "device_ids": ["urn:ngsi-ld:Building:001"],
                    "measure_ids": ["temperature"],
                    "options": {
                        "tenant": "tenant",
                        "scope": "scope",
                        "period": [
                            {
                                "months": [0],
                                "month_days": [1],
                                "week_days": [0],
                                "hours": [["12:00:00", "15:00:00"]],
                                "timezone": "UTC",
                            }
                        ],
                    },
                },
                True,
            ),
            (
                {
                    "device_ids": ["urn:ngsi-ld:Building:001"],
                    "measure_ids": ["temperature"],
                    "options": {
                        "tenant": "tenant",
                        "scope": "scope",
                        "period": [
                            {
                                "months": [0],
                                "month_days": [1],
                                "week_days": [0],
                                "hours": [["12:00:00", "15:00:00"]],
                                "timezone": "Europe/Madrid",
                            }
                        ],
                    },
                },
                True,
            ),
            (
                {
                    "device_ids": ["urn:ngsi-ld:Building:001"],
                    "measure_ids": ["temperature"],
                    "options": {
                        "tenant": "tenant",
                        "scope": "scope",
                        "period": [
                            {
                                "months": [0],
                                "month_days": [1],
                                "week_days": [0],
                                "hours": [["12:00:00", "15:00:00"]],
                                "timezone": "Europe/Zaragoza",
                            }
                        ],
                    },
                },
                False,
            ),
        ],
    )
    def test_where_clause_in_request(self, params: dict, valid: bool):
        try:
            TimeSeriesRequest(**params)
            assert valid
        except Exception as e:
            assert not valid
