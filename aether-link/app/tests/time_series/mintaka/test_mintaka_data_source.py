import datetime
import uuid
import requests
from app.core.time_series.data_sources.mintaka.mintaka_data_source import (
    MintakaDataSource,
)
from aether_pylib.time_series.time_series import TimeSeries, TimeSeriesValue
import app.tests.time_series.mintaka.test_mintaka_cases as test_cases
import pytest
import numpy as np


@pytest.fixture
def data_source_config():
    return {
        "MINTAKA_SERVICE_URL": "http://mintaka:8080",
        "DEFAULT_TENANT": "test_tenant",
        "CONTEXT_URL": "http://ngsi-ld-context:1026",
    }


@pytest.fixture
def mintaka_data_source(data_source_config):
    return MintakaDataSource(**data_source_config)


class TestMintakaDataSource:
    def test_mintaka_data_source_building(self, data_source_config):
        mintaka_data_source = MintakaDataSource(**data_source_config)
        assert mintaka_data_source.service_url == "http://mintaka:8080"
        assert mintaka_data_source.tenant == "test_tenant"
        assert mintaka_data_source.context_url == "http://ngsi-ld-context:1026"

    @pytest.mark.parametrize(
        (
            "entity_id",
            "measure_ids",
            "time_series_request_options",
            "expected_http_request",
        ),
        test_cases.http_request_building_test_cases,
    )
    def test_mintaka_query_building(
        self,
        mintaka_data_source,
        entity_id,
        measure_ids,
        time_series_request_options,
        expected_http_request,
    ):
        def compare_request(http_built_request, expected_request):
            print(http_built_request.url)

            # get params from url and compare them to expected params
            url = http_built_request.url

            split_url = url.split("?")

            base_url = split_url[0]

            params = split_url[1].split("&")

            assert base_url == expected_request["url"]

            for param in params:
                key, value = param.split("=")
                # remove spaces (+ is encoded space)
                value = value.replace("+", "")
                value = requests.utils.unquote(value)
                expected_url_encoded_value = str(expected_request["params"][key])
                assert value == expected_url_encoded_value

            for header in expected_request["headers"]:
                assert (
                    http_built_request.headers[header]
                    == expected_request["headers"][header]
                )

        session = requests.Session()
        query = mintaka_data_source._MintakaDataSource__get_query_from_options(
            entity_id, measure_ids, time_series_request_options, session
        )

        # compare request to expected request
        compare_request(query, expected_http_request)

    @pytest.mark.parametrize(
        ("ngsi_ld_response", "required_measures", "expected_time_series_response"),
        test_cases.ngsi_ld_response_transformation_test_cases,
    )
    def test_ngsi_ld_response_transformation(
        self,
        mintaka_data_source,
        ngsi_ld_response,
        required_measures,
        expected_time_series_response,
    ):
        time_series = (
            mintaka_data_source._MintakaDataSource__transform_ngsi_ld_response(
                ngsi_ld_response, required_measures
            )
        )

        assert time_series == expected_time_series_response

    @pytest.mark.parametrize(
        ("options", "ts_length", "latest_date", "expected_remaining_data_options"),
        test_cases.remaining_options_test_cases,
    )
    def test_get_remaining_data_options(
        self,
        mintaka_data_source,
        options,
        ts_length,
        latest_date,
        expected_remaining_data_options,
    ):
        def random_rime_series(
            lenght: int, latest_date: datetime.datetime
        ) -> TimeSeries:
            random_device_id = str(uuid.uuid4())
            random_measure_id = str(uuid.uuid4())
            values = []

            for i in range(lenght):
                random_value = np.random.rand()

                random_timestamp = latest_date + datetime.timedelta(minutes=i)

                values.append(
                    TimeSeriesValue(
                        timestamp=random_timestamp.isoformat(),
                        value=random_value,
                    )
                )

            return TimeSeries(
                device_id=random_device_id,
                measure_id=random_measure_id,
                values=values,
            )

        random_ts = random_rime_series(ts_length, latest_date)
        assert len(random_ts.values) == ts_length

        remaining_data_options = (
            mintaka_data_source._MintakaDataSource__get_remaining_data_options(
                random_ts, options
            )
        )

        assert remaining_data_options == expected_remaining_data_options

    @pytest.mark.parametrize(
        ("options_list", "expected_options"), test_cases.merge_options_test_cases
    )
    def test_merge_options(self, mintaka_data_source, options_list, expected_options):
        merged_options = mintaka_data_source._MintakaDataSource__merge_options(
            options_list
        )

        assert merged_options == expected_options

    def test_merge_timeseries(self, mintaka_data_source):
        def random_timeseries(
            lenght,
            device,
            measure,
            start_date=datetime.datetime.fromisoformat("2020-01-01T00:00:00"),
        ):
            values = []
            for i in range(lenght):
                random_value = np.random.rand()
                random_timestamp = start_date + datetime.timedelta(minutes=i)
                values.append(
                    TimeSeriesValue(
                        timestamp=random_timestamp.isoformat(),
                        value=random_value,
                    )
                )

            return TimeSeries(
                device_id=device,
                measure_id=measure,
                values=values,
            )

        def get_num_unique_timestamps(map, key):
            return len(set([ts.timestamp for ts in map[key]]))

        d1_m1_a = random_timeseries(10, "device1", "measure1")
        d1_m2_a = random_timeseries(10, "device1", "measure2")
        d2_m1_a = random_timeseries(10, "device2", "measure1")
        d2_m2_a = random_timeseries(10, "device2", "measure2")

        d1_m1_b = random_timeseries(20, "device1", "measure1")
        d2_m2_b = random_timeseries(20, "device2", "measure2")
        d2_m3_b = random_timeseries(50, "device2", "measure3")

        merged = mintaka_data_source._MintakaDataSource__merge_time_series(
            [d1_m1_a, d1_m2_a, d2_m1_a, d2_m2_a], [d1_m1_b, d2_m2_b, d2_m3_b]
        )

        assert len(merged) == 5

        dm_map = {(ts.device_id, ts.measure_id): ts.values for ts in merged}

        assert len(dm_map[("device1", "measure1")]) == 20
        assert get_num_unique_timestamps(dm_map, ("device1", "measure1")) == 20

        assert len(dm_map[("device1", "measure2")]) == 10
        assert get_num_unique_timestamps(dm_map, ("device1", "measure2")) == 10

        assert len(dm_map[("device2", "measure1")]) == 10
        assert get_num_unique_timestamps(dm_map, ("device2", "measure1")) == 10

        assert len(dm_map[("device2", "measure2")]) == 20
        assert get_num_unique_timestamps(dm_map, ("device2", "measure2")) == 20

        assert len(dm_map[("device2", "measure3")]) == 50
        assert get_num_unique_timestamps(dm_map, ("device2", "measure3")) == 50

    @pytest.mark.parametrize(
        ("period_options"),
        test_cases.period_filtering_test_cases,
    )
    def test_period_filtering(self, mintaka_data_source, period_options):
        def random_time_series(year):
            # one data for each day of the year, and hour
            delta_time = datetime.timedelta(hours=1)
            current_date = datetime.datetime(year, 1, 1, 0, 0, 0)

            values = []
            while current_date.year == year:
                values.append(
                    TimeSeriesValue(
                        timestamp=current_date.isoformat(),
                        value=np.random.rand(),
                    )
                )
                current_date += delta_time

            return TimeSeries(
                device_id="device1",
                measure_id="measure1",
                values=values,
            )

        def not_none_or_empty(list):
            return list is not None and len(list) > 0

        time_series = random_time_series(2023)

        filtered_time_series = (
            mintaka_data_source._MintakaDataSource__period_list_series_filtering(
                time_series, [period_options]
            )
        )

        # check that all ts are in the correct period
        for ts in filtered_time_series.values:
            if not_none_or_empty(period_options.months):
                month = ts.timestamp.month - 1
                assert month in period_options.months

            if not_none_or_empty(period_options.month_days):
                month_day = ts.timestamp.day - 1
                assert month_day in period_options.month_days

            if not_none_or_empty(period_options.week_days):
                week_day = ts.timestamp.weekday()
                assert week_day in period_options.week_days

            if not_none_or_empty(period_options.hours):
                time = ts.timestamp.time()
                for hour in period_options.hours:
                    start = hour[0]
                    end = hour[1]
                    if end < start:
                        if time >= start or time <= end:
                            break
                    else:
                        if start <= time <= end:
                            break
                else:
                    assert False, f"ts {ts.timestamp} should be excluded"

    @pytest.mark.parametrize(
        ("period_options"),
        test_cases.period_filtering_adjustments_test_cases,
    )
    def test_period_filtering_adjustments(self, mintaka_data_source, period_options):
        def random_time_series(year):
            # one data for each day of the year, and hour
            delta_time = datetime.timedelta(hours=1)
            current_date = datetime.datetime(year, 1, 1, 0, 0, 0)

            values = []
            while current_date.year == year:
                values.append(
                    TimeSeriesValue(
                        timestamp=current_date.isoformat(),
                        value=np.random.rand(),
                    )
                )
                current_date += delta_time

            return TimeSeries(
                device_id="device1",
                measure_id="measure1",
                values=values,
            )

        time_series = random_time_series(2023)

        filtered_time_series = (
            mintaka_data_source._MintakaDataSource__period_list_series_filtering(
                time_series, [period_options]
            )
        )

        # check that excluded dates are not in the filtered time series
        # and that included dates are in the filtered time series

        expected_includes = sum(
            [24 for extra in period_options.extra if not extra.exclude]
        )

        current_includes = 0
        for ts in filtered_time_series.values:
            for extra in period_options.extra:
                if (
                    extra.year == ts.timestamp.year
                    and extra.month == ts.timestamp.month - 1
                    and extra.month_day == ts.timestamp.day - 1
                ):
                    if extra.exclude:
                        assert False, f"ts {ts.timestamp} should be excluded"
                    else:
                        current_includes += 1
                        assert True

        assert current_includes == expected_includes
