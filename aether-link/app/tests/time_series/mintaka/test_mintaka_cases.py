"""
Test cases for time-series module
Builded in this file so the test file is cleaner

WARNING: avoid auto-formatting this code, because it might include some extra brackets
and that will break the tests
"""

import datetime
from aether_pylib.time_series.time_series import TimeSeries, TimeSeriesValue
from aether_pylib.time_series.time_scope import TimeScope, TimeScopeAdjustment
from aether_pylib.time_series.time_series_options import (
    TimeSeriesOptions,
)


http_request_building_test_cases = [
    (
        # entity id
        "urn:ngsi-ld:device:SampleDevice01",
        # measure ids
        ["measure01"],
        # time series options
        TimeSeriesOptions(
            **{
                "start_date": "2020-01-01T00:00:00Z",
                "end_date": "2020-01-02T00:00:00Z",
                "order": "asc",
                "limit": 100,
                "aggregation": {
                    "type": "mean",
                    "interval": "PT35S",
                },
                "tenant": "test_tenant",
                "scope": "test_scope",
            }
        ),
        # expected http request
        {
            "url": "http://mintaka:8080/temporal/entities/urn:ngsi-ld:device:SampleDevice01",
            "headers": {
                "NGSILD-Tenant": "test_tenant",
                "link": '<http://ngsi-ld-context:1026>; rel="http://www.w3.org/ns/json-ld#context"; type="application/ld+json"',
            },
            "params": {
                "attrs": "measure01",
                "timerel": "between",
                "timeAt": "2020-01-01T00:00:00+00:00",
                "endTimeAt": "2020-01-02T00:00:00+00:00",
                "lastN": 100,
            },
        },
    ),
    (
        # entity id
        "urn:ngsi-ld:device:SampleDevice01",
        # measure ids
        ["measure01"],
        # time series options
        TimeSeriesOptions(
            **{
                "start_date": "2020-01-01T00:00:00Z",
                "end_date": "2020-01-02T00:00:00Z",
                "order": "asc",
                "limit": 100,
                "aggregation": {
                    "type": "mean",
                    "interval": "PT35S",
                },
                "tenant": "test_tenant",
                "scope": "test_scope",
            }
        ),
        # expected http request
        {
            "url": "http://mintaka:8080/temporal/entities/urn:ngsi-ld:device:SampleDevice01",
            "headers": {
                "NGSILD-Tenant": "test_tenant",
                "link": '<http://ngsi-ld-context:1026>; rel="http://www.w3.org/ns/json-ld#context"; type="application/ld+json"',
            },
            "params": {
                "attrs": "measure01",
                "timerel": "between",
                "timeAt": "2020-01-01T00:00:00+00:00",
                "endTimeAt": "2020-01-02T00:00:00+00:00",
                "lastN": 100,
            },
        },
    ),
    (
        # entity id
        "urn:ngsi-ld:device:SampleDevice01",
        # measure ids
        ["measure01"],
        # time series options
        TimeSeriesOptions(
            **{
                "start_date": "2020-01-01T00:00:00Z",
                "order": "asc",
                "limit": 100,
                "aggregation": {
                    "type": "mean",
                    "interval": "PT35S",
                },
                "tenant": "test_tenant",
                "scope": "test_scope",
            }
        ),
        # expected http request
        {
            "url": "http://mintaka:8080/temporal/entities/urn:ngsi-ld:device:SampleDevice01",
            "headers": {
                "NGSILD-Tenant": "test_tenant",
                "link": '<http://ngsi-ld-context:1026>; rel="http://www.w3.org/ns/json-ld#context"; type="application/ld+json"',
            },
            "params": {
                "attrs": "measure01",
                "timerel": "after",
                "timeAt": "2020-01-01T00:00:00+00:00",
                "lastN": 100,
            },
        },
    ),
    (
        # entity id
        "urn:ngsi-ld:device:SampleDevice01",
        # measure ids
        ["measure01"],
        # time series options
        TimeSeriesOptions(
            **{
                "end_date": "2020-01-01T00:00:00Z",
                "order": "asc",
                "limit": 100,
                "aggregation": {
                    "type": "mean",
                    "interval": "PT35S",
                },
                "tenant": "test_tenant",
                "scope": "test_scope",
            }
        ),
        # expected http request
        {
            "url": "http://mintaka:8080/temporal/entities/urn:ngsi-ld:device:SampleDevice01",
            "headers": {
                "NGSILD-Tenant": "test_tenant",
                "link": '<http://ngsi-ld-context:1026>; rel="http://www.w3.org/ns/json-ld#context"; type="application/ld+json"',
            },
            "params": {
                "attrs": "measure01",
                "timerel": "before",
                "timeAt": "2020-01-01T00:00:00+00:00",
                "lastN": 100,
            },
        },
    ),
    (
        # entity id
        "urn:ngsi-ld:device:SampleDevice01",
        # measure ids
        ["measure01"],
        # time series options
        TimeSeriesOptions(
            **{
                "start_date": "2020-01-01T00:00:00Z",
                "end_date": "2020-01-02T00:00:00Z",
                "order": "asc",
                "aggregation": {
                    "type": "mean",
                    "interval": "PT35S",
                },
                "tenant": "test_tenant",
                "scope": "test_scope",
            }
        ),
        # expected http request
        {
            "url": "http://mintaka:8080/temporal/entities/urn:ngsi-ld:device:SampleDevice01",
            "headers": {
                "NGSILD-Tenant": "test_tenant",
                "link": '<http://ngsi-ld-context:1026>; rel="http://www.w3.org/ns/json-ld#context"; type="application/ld+json"',
            },
            "params": {
                "attrs": "measure01",
                "timerel": "between",
                "timeAt": "2020-01-01T00:00:00+00:00",
                "endTimeAt": "2020-01-02T00:00:00+00:00",
                "lastN": 100,
            },
        },
    ),
    (
        # entity id
        "urn:ngsi-ld:device:SampleDevice01",
        # measure ids
        ["measure01, measure02"],
        # time series options
        TimeSeriesOptions(
            **{
                "start_date": "2020-01-01T00:00:00Z",
                "end_date": "2020-01-02T00:00:00Z",
                "order": "asc",
                "limit": 100,
                "aggregation": {
                    "type": "mean",
                    "interval": "PT35S",
                },
                "tenant": "test_tenant",
                "scope": "test_scope",
            }
        ),
        # expected http request
        {
            "url": "http://mintaka:8080/temporal/entities/urn:ngsi-ld:device:SampleDevice01",
            "headers": {
                "NGSILD-Tenant": "test_tenant",
                "link": '<http://ngsi-ld-context:1026>; rel="http://www.w3.org/ns/json-ld#context"; type="application/ld+json"',
            },
            "params": {
                "attrs": "measure01,measure02",
                "timerel": "between",
                "timeAt": "2020-01-01T00:00:00+00:00",
                "endTimeAt": "2020-01-02T00:00:00+00:00",
                "lastN": 100,
            },
        },
    ),
]


ngsi_ld_response_transformation_test_cases = [
    (
        # ngsi-ld response
        {
            "id": "urn:ngsi-ld:device:SampleDevice01",
            "type": "device",
            "measure01": [
                {
                    "type": "Property",
                    "value": 100.0,
                    "observedAt": "2020-01-01T00:00:00Z",
                },
                {
                    "type": "Property",
                    "value": 200.0,
                    "observedAt": "2020-01-01T00:00:01Z",
                },
            ],
        },
        # measure ids to extract
        ["measure01"],
        # expected time series
        [
            TimeSeries(
                **{
                    "device_id": "urn:ngsi-ld:device:SampleDevice01",
                    "measure_id": "measure01",
                    "values": [
                        TimeSeriesValue(
                            **{"timestamp": "2020-01-01T00:00:00+00:00", "value": 100.0}
                        ),
                        TimeSeriesValue(
                            **{"timestamp": "2020-01-01T00:00:01+00:00", "value": 200.0}
                        ),
                    ],
                }
            )
        ],
    ),
    # (
    #     # ngsi-ld response
    #     {
    #         "id": "urn:ngsi-ld:device:SampleDevice01",
    #         "type": "device",
    #         "measure01": [
    #             {
    #                 "type": "Property",
    #                 "value": 100.0,
    #                 "observedAt": "2020-01-01T00:00:00Z",
    #             },
    #             {
    #                 "type": "Property",
    #                 "value": 200.0,
    #                 "observedAt": "2020-01-01T00:00:01Z",
    #             },
    #         ],
    #         "measure02": [
    #             {
    #                 "type": "Property",
    #                 "value": 400.0,
    #                 "observedAt": "2021-01-01T00:00:00Z",
    #             },
    #             {
    #                 "type": "Property",
    #                 "value": 500.0,
    #                 "observedAt": "2021-01-01T00:00:01Z",
    #             },
    #         ],
    #     },
    #     # measure ids to extract
    #     ["measure01"],
    #     # expected time series
    #     [
    #         TimeSeries(
    #             **{
    #                 "device_id": "urn:ngsi-ld:device:SampleDevice01",
    #                 "measure_id": "measure01",
    #                 "values": [
    #                     TimeSeriesValue(
    #                         **{"timestamp": "2020-01-01T00:00:00+00:00", "value": 100.0}
    #                     ),
    #                     TimeSeriesValue(
    #                         **{"timestamp": "2020-01-01T00:00:01+00:00", "value": 200.0}
    #                     ),
    #                 ],
    #             }
    #         )
    #     ],
    # ),
    # (
    #     # ngsi-ld response
    #     {
    #         "id": "urn:ngsi-ld:device:SampleDevice01",
    #         "type": "device",
    #         "measure01": [
    #             {
    #                 "type": "Property",
    #                 "value": 100.0,
    #                 "observedAt": "2020-01-01T00:00:00Z",
    #             },
    #             {
    #                 "type": "Property",
    #                 "value": 200.0,
    #                 "observedAt": "2020-01-01T00:00:01Z",
    #             },
    #         ],
    #         "measure02": [
    #             {
    #                 "type": "Property",
    #                 "value": 400.0,
    #                 "observedAt": "2021-01-01T00:00:00Z",
    #             },
    #             {
    #                 "type": "Property",
    #                 "value": 500.0,
    #                 "observedAt": "2021-01-01T00:00:01Z",
    #             },
    #         ],
    #     },
    #     # measure ids to extract
    #     ["measure01", "measure02"],
    #     # expected time series
    #     [
    #         TimeSeries(
    #             **{
    #                 "device_id": "urn:ngsi-ld:device:SampleDevice01",
    #                 "measure_id": "measure01",
    #                 "values": [
    #                     TimeSeriesValue(
    #                         **{"timestamp": "2020-01-01T00:00:00+00:00", "value": 100.0}
    #                     ),
    #                     TimeSeriesValue(
    #                         **{"timestamp": "2020-01-01T00:00:01+00:00", "value": 200.0}
    #                     ),
    #                 ],
    #             }
    #         ),
    #         TimeSeries(
    #             **{
    #                 "device_id": "urn:ngsi-ld:device:SampleDevice01",
    #                 "measure_id": "measure02",
    #                 "values": [
    #                     TimeSeriesValue(
    #                         **{"timestamp": "2021-01-01T00:00:00+00:00", "value": 400.0}
    #                     ),
    #                     TimeSeriesValue(
    #                         **{"timestamp": "2021-01-01T00:00:01+00:00", "value": 500.0}
    #                     ),
    #                 ],
    #             }
    #         ),
    #     ],
    # ),
    # (
    #     # ngsi-ld response
    #     {
    #         "id": "urn:ngsi-ld:device:SampleDevice01",
    #         "type": "device",
    #         "measure01": [
    #             {
    #                 "type": "Property",
    #                 "value": 100.0,
    #                 "timestamp": "2020-01-01T00:00:00Z",
    #             },
    #             {
    #                 "type": "Property",
    #                 "value": 200.0,
    #                 "observedAt": "2020-01-01T00:00:01Z",
    #             },
    #         ],
    #         "measure02": [
    #             {
    #                 "type": "Property",
    #                 "value": 400.0,
    #                 "observedAt": "2021-01-01T00:00:00Z",
    #             },
    #             {
    #                 "type": "Property",
    #                 "@value": 500.0,
    #                 "createdAt": "2021-01-01T00:00:01Z",
    #             },
    #         ],
    #     },
    #     # measure ids to extract
    #     ["measure01", "measure02"],
    #     # expected time series
    #     [
    #         TimeSeries(
    #             **{
    #                 "device_id": "urn:ngsi-ld:device:SampleDevice01",
    #                 "measure_id": "measure01",
    #                 "values": [
    #                     TimeSeriesValue(
    #                         **{"timestamp": "2020-01-01T00:00:00+00:00", "value": 100.0}
    #                     ),
    #                     TimeSeriesValue(
    #                         **{"timestamp": "2020-01-01T00:00:01+00:00", "value": 200.0}
    #                     ),
    #                 ],
    #             }
    #         ),
    #         TimeSeries(
    #             **{
    #                 "device_id": "urn:ngsi-ld:device:SampleDevice01",
    #                 "measure_id": "measure02",
    #                 "values": [
    #                     TimeSeriesValue(
    #                         **{"timestamp": "2021-01-01T00:00:00+00:00", "value": 400.0}
    #                     ),
    #                     TimeSeriesValue(
    #                         **{"timestamp": "2021-01-01T00:00:01+00:00", "value": 500.0}
    #                     ),
    #                 ],
    #             }
    #         ),
    #     ],
    # ),
]


remaining_options_test_cases = [
    (
        TimeSeriesOptions(
            start_date="2020-01-01T00:00:00",
            end_date="2020-01-01T00:03:00",
            order="asc",
            aggregation=None,
            period=None,
            limit=100,
            tenant="test_tenant",
            scope="test_scope",
        ),
        20,
        datetime.datetime.fromisoformat("2020-01-01T00:02:00"),
        TimeSeriesOptions(
            start_date="2020-01-01T00:00:00",
            end_date=(
                datetime.datetime.fromtimestamp(
                    datetime.datetime.fromisoformat("2020-01-01T00:02:00").timestamp()
                    - 1
                ).isoformat()
            ),
            order="asc",
            aggregation=None,
            period=None,
            limit=80,
            tenant="test_tenant",
            scope="test_scope",
        ),
    ),
    (
        TimeSeriesOptions(
            start_date="2020-01-01T00:00:00",
            end_date="2020-01-01T00:03:00",
            order="asc",
            aggregation=None,
            period=None,
            limit=100,
            tenant="test_tenant",
            scope="test_scope",
        ),
        200,
        datetime.datetime.fromisoformat("2020-01-01T00:02:00"),
        None,
    ),
    (
        TimeSeriesOptions(
            start_date=None,
            end_date=None,
            order="asc",
            aggregation=None,
            period=None,
            limit=100,
            tenant="test_tenant",
            scope="test_scope",
        ),
        20,
        datetime.datetime.fromisoformat("2020-01-01T00:02:00"),
        TimeSeriesOptions(
            start_date=None,
            end_date=(
                datetime.datetime.fromtimestamp(
                    datetime.datetime.fromisoformat("2020-01-01T00:02:00").timestamp()
                    - 1
                ).isoformat()
            ),
            order="asc",
            aggregation=None,
            period=None,
            limit=80,
            tenant="test_tenant",
            scope="test_scope",
        ),
    ),
    (
        TimeSeriesOptions(
            start_date="2020-01-01T00:00:00",
            end_date=None,
            order="asc",
            aggregation=None,
            period=None,
            limit=100,
            tenant="test_tenant",
            scope="test_scope",
        ),
        20,
        datetime.datetime.fromisoformat("2020-01-01T00:02:00"),
        TimeSeriesOptions(
            start_date="2020-01-01T00:00:00",
            end_date=(
                datetime.datetime.fromtimestamp(
                    datetime.datetime.fromisoformat("2020-01-01T00:02:00").timestamp()
                    - 1
                ).isoformat()
            ),
            order="asc",
            aggregation=None,
            period=None,
            limit=80,
            tenant="test_tenant",
            scope="test_scope",
        ),
    ),
    (
        TimeSeriesOptions(
            start_date="2020-01-01T00:01:00",
            end_date=None,
            order="asc",
            aggregation=None,
            period=None,
            limit=100,
            tenant="test_tenant",
            scope="test_scope",
        ),
        20,
        datetime.datetime.fromisoformat("2020-01-01T00:00:00"),
        None,
    ),
]

merge_options_test_cases = [
    (
        [
            TimeSeriesOptions(
                start_date="2020-01-02T00:00:00",
                end_date="2020-01-01T00:03:00",
                order="asc",
                aggregation=None,
                period=None,
                limit=100,
                tenant="test_tenant",
                scope="test_scope",
            ),
            TimeSeriesOptions(
                start_date="2020-01-01T00:00:00",
                end_date="2020-01-01T00:05:00",
                order="asc",
                aggregation=None,
                period=None,
                limit=200,
                tenant="test_tenant",
                scope="test_scope",
            ),
        ],
        TimeSeriesOptions(
            start_date="2020-01-01T00:00:00",
            end_date="2020-01-01T00:05:00",
            order="asc",
            aggregation=None,
            period=None,
            limit=200,
            tenant="test_tenant",
            scope="test_scope",
        ),
    ),
    (
        [
            TimeSeriesOptions(
                start_date=None,
                end_date=None,
                order="asc",
                aggregation=None,
                period=None,
                limit=100,
                tenant="test_tenant",
                scope="test_scope",
            ),
            TimeSeriesOptions(
                start_date=None,
                end_date=None,
                order="asc",
                aggregation=None,
                period=None,
                limit=200,
                tenant="test_tenant",
                scope="test_scope",
            ),
        ],
        TimeSeriesOptions(
            start_date=None,
            end_date=None,
            order="asc",
            aggregation=None,
            period=None,
            limit=200,
            tenant="test_tenant",
            scope="test_scope",
        ),
    ),
    (
        [
            TimeSeriesOptions(
                start_date="2020-01-02T00:00:00",
                end_date=None,
                order="asc",
                aggregation=None,
                period=None,
                limit=250,
                tenant="test_tenant",
                scope="test_scope",
            ),
            TimeSeriesOptions(
                start_date=None,
                end_date="2020-01-04T00:05:00",
                order="asc",
                aggregation=None,
                period=None,
                limit=200,
                tenant="test_tenant",
                scope="test_scope",
            ),
        ],
        TimeSeriesOptions(
            start_date="2020-01-02T00:00:00",
            end_date="2020-01-04T00:05:00",
            order="asc",
            aggregation=None,
            period=None,
            limit=250,
            tenant="test_tenant",
            scope="test_scope",
        ),
    ),
]

period_filtering_test_cases = [
    # period options
    TimeScope(
        months=[0, 1],
        month_days=[0, 1],
        week_days=[],
        hours=[],
    ),
    TimeScope(
        months=[0, 1, 2],
        month_days=[10, 20, 30],
        week_days=[1, 3, 5],
        hours=[[datetime.time(12, 0, 0), datetime.time(15, 0, 0)]],
    ),
    TimeScope(
        months=[0, 1, 2, 5],
        month_days=[10, 20, 30],
        week_days=[1, 3, 5],
        hours=[
            [datetime.time(12, 0, 0), datetime.time(15, 0, 0)],
            [datetime.time(18, 0, 0), datetime.time(21, 0, 0)],
        ],
    ),
    TimeScope(
        months=[0, 1, 2, 5],
        month_days=[10, 20, 30],
        week_days=[1, 3, 5],
        hours=[
            [datetime.time(12, 0, 0), datetime.time(15, 0, 0)],
            [datetime.time(18, 0, 0), datetime.time(21, 0, 0)],
            [datetime.time(18, 0, 0), datetime.time(3, 0, 0)],
        ],
    ),
]

period_filtering_adjustments_test_cases = [
    TimeScope(
        months=[0, 1],
        month_days=[0, 1],
        week_days=[],
        hours=[],
        extra=[
            TimeScopeAdjustment(
                year=2023,
                month=1,
                month_day=1,
                exclude=True,
            ),
        ],
    ),
    TimeScope(
        months=[0, 1],
        month_days=[0, 1],
        week_days=[],
        hours=[],
        extra=[
            TimeScopeAdjustment(
                year=2023,
                month=2,
                month_day=1,
                exclude=False,
            ),
        ],
    ),
    TimeScope(
        months=[0, 1],
        month_days=[0, 1],
        week_days=[],
        hours=[],
        extra=[
            TimeScopeAdjustment(
                year=2023,
                month=1,
                month_day=1,
                exclude=True,
            ),
            TimeScopeAdjustment(
                year=2023,
                month=2,
                month_day=1,
                exclude=False,
            ),
        ],
    ),
    TimeScope(
        months=[0, 1],
        month_days=[0, 1],
        week_days=[],
        hours=[],
        extra=[
            TimeScopeAdjustment(
                year=2023,
                month=1,
                month_day=1,
                exclude=True,
            ),
            TimeScopeAdjustment(
                year=2023,
                month=0,
                month_day=1,
                exclude=True,
            ),
            TimeScopeAdjustment(
                year=2023,
                month=2,
                month_day=1,
                exclude=False,
            ),
        ],
    ),
    TimeScope(
        months=[0, 1],
        month_days=[0, 1],
        week_days=[],
        hours=[],
        extra=[
            TimeScopeAdjustment(
                year=2023,
                month=1,
                month_day=1,
                exclude=True,
            ),
            TimeScopeAdjustment(
                year=2023,
                month=0,
                month_day=1,
                exclude=True,
            ),
            TimeScopeAdjustment(
                year=2023,
                month=2,
                month_day=1,
                exclude=False,
            ),
            TimeScopeAdjustment(
                year=2023,
                month=3,
                month_day=1,
                exclude=False,
            ),
        ],
    ),
]
