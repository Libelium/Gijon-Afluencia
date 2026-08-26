from datetime import datetime
from aether_pylib.time_series.time_series_options import (
    TimeSeriesAggregationOptions,
)
import pytest

from aether_pylib.time_series.time_series import TimeSeriesValue
from app.core.time_series.aggregations import aggregate


def sample_time_series():
    return [
        TimeSeriesValue(timestamp="2020-01-01T00:00:00Z", value=1.0),
        TimeSeriesValue(timestamp="2020-01-01T01:00:00Z", value=2.0),
        TimeSeriesValue(timestamp="2020-01-01T02:00:00Z", value=3.0),
        TimeSeriesValue(timestamp="2020-01-01T03:00:00Z", value=4.0),
    ]


class TestAggregations:
    @pytest.mark.parametrize(
        ("time_series", "aggregation_options", "expected_time_series"),
        [
            (
                sample_time_series(),
                TimeSeriesAggregationOptions(**{"type": "mean", "interval": "PT30M"}),
                [
                    TimeSeriesValue(timestamp="2020-01-01T00:00:00Z", value=1.0),
                    TimeSeriesValue(timestamp="2020-01-01T00:30:00Z", value=1.0),
                    TimeSeriesValue(timestamp="2020-01-01T01:00:00Z", value=2.0),
                    TimeSeriesValue(timestamp="2020-01-01T01:30:00Z", value=2.0),
                    TimeSeriesValue(timestamp="2020-01-01T02:00:00Z", value=3.0),
                    TimeSeriesValue(timestamp="2020-01-01T02:30:00Z", value=3.0),
                    TimeSeriesValue(timestamp="2020-01-01T03:00:00Z", value=4.0),
                ],
            ),
            (
                sample_time_series(),
                TimeSeriesAggregationOptions(**{"type": "max", "interval": "PT30M"}),
                [
                    TimeSeriesValue(timestamp="2020-01-01T00:00:00Z", value=1.0),
                    TimeSeriesValue(timestamp="2020-01-01T00:30:00Z", value=1.0),
                    TimeSeriesValue(timestamp="2020-01-01T01:00:00Z", value=2.0),
                    TimeSeriesValue(timestamp="2020-01-01T01:30:00Z", value=2.0),
                    TimeSeriesValue(timestamp="2020-01-01T02:00:00Z", value=3.0),
                    TimeSeriesValue(timestamp="2020-01-01T02:30:00Z", value=3.0),
                    TimeSeriesValue(timestamp="2020-01-01T03:00:00Z", value=4.0),
                ],
            ),
            (
                sample_time_series(),
                TimeSeriesAggregationOptions(**{"type": "min", "interval": "PT30M"}),
                [
                    TimeSeriesValue(timestamp="2020-01-01T00:00:00Z", value=1.0),
                    TimeSeriesValue(timestamp="2020-01-01T00:30:00Z", value=1.0),
                    TimeSeriesValue(timestamp="2020-01-01T01:00:00Z", value=2.0),
                    TimeSeriesValue(timestamp="2020-01-01T01:30:00Z", value=2.0),
                    TimeSeriesValue(timestamp="2020-01-01T02:00:00Z", value=3.0),
                    TimeSeriesValue(timestamp="2020-01-01T02:30:00Z", value=3.0),
                    TimeSeriesValue(timestamp="2020-01-01T03:00:00Z", value=4.0),
                ],
            ),
            (
                sample_time_series(),
                TimeSeriesAggregationOptions(**{"type": "sum", "interval": "PT30M"}),
                [
                    TimeSeriesValue(timestamp="2020-01-01T00:00:00Z", value=1.0),
                    TimeSeriesValue(timestamp="2020-01-01T00:30:00Z", value=0.0),
                    TimeSeriesValue(timestamp="2020-01-01T01:00:00Z", value=2.0),
                    TimeSeriesValue(timestamp="2020-01-01T01:30:00Z", value=0.0),
                    TimeSeriesValue(timestamp="2020-01-01T02:00:00Z", value=3.0),
                    TimeSeriesValue(timestamp="2020-01-01T02:30:00Z", value=0.0),
                    TimeSeriesValue(timestamp="2020-01-01T03:00:00Z", value=4.0),
                ],
            ),
            (
                sample_time_series(),
                TimeSeriesAggregationOptions(**{"type": "sum", "interval": "PT3H"}),
                [
                    TimeSeriesValue(timestamp="2020-01-01T00:00:00Z", value=6.0),
                    TimeSeriesValue(timestamp="2020-01-01T03:00:00Z", value=4.0),
                ],
            ),
            (
                sample_time_series(),
                TimeSeriesAggregationOptions(**{"type": "moving_avg", "interval": "PT30M"}),
                [
                    TimeSeriesValue(timestamp="2020-01-01T00:00:00Z", value=1.0),
                    TimeSeriesValue(timestamp="2020-01-01T01:00:00Z", value=2.0),
                    TimeSeriesValue(timestamp="2020-01-01T02:00:00Z", value=3.0),
                    TimeSeriesValue(timestamp="2020-01-01T03:00:00Z", value=4.0),
                ]
            ),
            (
                sample_time_series(),
                TimeSeriesAggregationOptions(**{"type": "percentile-7", "interval": "PT4H"}),
                [
                    TimeSeriesValue(timestamp="2020-01-01T00:00:00Z", value=1.21),
                ]
            )
        ],
    )
    def test_aggregations(self, time_series, aggregation_options, expected_time_series):
        def compare_time_series_lists(time_series_list1, time_series_list2):
            assert len(time_series_list1) == len(time_series_list2)
            for i in range(len(time_series_list1)):
                assert time_series_list1[i].value == time_series_list2[i].value
                assert time_series_list1[i].timestamp == time_series_list2[i].timestamp

        aggregation = aggregate(aggregation_options, time_series)

        # invert the list because when this test was done, the 
        # aggregation was done in reverse order
        aggregation.reverse()

        compare_time_series_lists(
            aggregation, expected_time_series
        )
