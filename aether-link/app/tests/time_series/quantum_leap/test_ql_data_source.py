from dataclasses import dataclass
import datetime
import dateutil.parser
from app.core.time_series.data_sources.quantum_leap.schemas.entity_schema import Entity
from aether_pylib.time_series.time_scope import TimeScopeAdjustment, TimeScope
from aether_pylib.time_series.time_series_options import (
    TimeSeriesOptions,
    TimeSeriesOrdering,
    WhereClause,
)
from aether_pylib.time_series.time_series_request import TimeSeriesRequest
import pytest
from app.tests.time_series.quantum_leap.mock_db import MockDb, DeviceTableModel

# global so database initialization is only done once
MOCK_DB = MockDb()


# a fixture that persists the state
@pytest.fixture
def mock_db():
    return MOCK_DB


@pytest.fixture(autouse=True)
def auto_clear_db():
    yield
    MOCK_DB.clear_data()


class TestQlDataSource:

    def add_one_year(
        self, mock_db: MockDb, device_id: str, year: int = 2020, hour_step: int = 24
    ):
        cm = mock_db.get_connection_manager()
        session = cm.get_session()

        # insert random data for each day of the year
        mock_db.update_ds_entity_tables(
            Entity(
                tenant="t1",
                scope="/",
                urn=f"device_1",
            )
        )

        this_date = dateutil.parser.parse(f"{year}-01-01T00:00:00Z")
        total = 365 * 24 // hour_step
        for i in range(total):
            device = DeviceTableModel(
                entity_id=device_id,
                entity_type="Device",
                time_index=this_date,
                fiware_servicepath="/",
                original_ngsi_entity={},
                instance_id="device",
                name_col=device_id,
                tmp_col=i,
                active_col=(i % 2 == 0),
                location_col={},
            )

            session.add(device)

            this_date = this_date + dateutil.relativedelta.relativedelta(
                hours=hour_step
            )

        session.commit()

    def test_db_init(self, mock_db: MockDb):
        """
        Testing the mock DB class itself, this is
        a meta test to ensure that the mock DB is working
        """

        # quet all devices
        cm = mock_db.get_connection_manager()

        session = cm.get_session()

        # query all devices
        devices = session.query(DeviceTableModel).all()

        assert len(devices) == 0

        # insert random devices
        for i in range(10):
            device = DeviceTableModel(
                entity_id=f"device_{i}",
                entity_type="device",
                time_index=dateutil.parser.parse("2020-01-01T00:00:00Z"),
                fiware_servicepath="/",
                original_ngsi_entity={},
                instance_id="device",
                name_col=f"device_{i}",
                tmp_col=25.0,
                active_col=True,
                location_col={},
            )

            session.add(device)

        session.commit()

        # query all devices
        devices = session.query(DeviceTableModel).all()

        assert len(devices) == 10

    def test_auto_clear(self, mock_db: MockDb):
        """
        Test that the database is cleared after each test
        """

        # all the devices
        cm = mock_db.get_connection_manager()
        session = cm.get_session()

        # query all devices
        devices = session.query(DeviceTableModel).all()

        assert len(devices) == 0

    def test_entity_selection(self, mock_db: MockDb):
        """
        Test that device ids and measure ids are retrieved correctly
        """

        cm = mock_db.get_connection_manager()
        session = cm.get_session()

        # insert random devices
        for i in range(10):
            device = DeviceTableModel(
                entity_id=f"device_{i}",
                entity_type="device",
                time_index=dateutil.parser.parse("2020-01-01T00:00:00Z"),
                fiware_servicepath="/",
                original_ngsi_entity={},
                instance_id="device",
                name_col=f"device_{i}",
                tmp_col=25.0,
                active_col=True,
                location_col={},
            )

            session.add(device)
            mock_db.update_ds_entity_tables(
                Entity(
                    tenant="",
                    scope="/",
                    urn=f"device_{i}",
                )
            )

        session.commit()

        # query all devices
        devices = session.query(DeviceTableModel).all()

        assert len(devices) == 10

        request = TimeSeriesRequest(
            device_ids=["device_1", "device_2"],
            measure_ids=["tmp", "false_measure"],
            options=TimeSeriesOptions(
                tenant="",
                scope="/",
            ),
        )

        # get the data source
        ds = mock_db.get_ql_ds()

        # get the time series
        time_series = ds.get_single_timeseries_request(request)

        assert time_series.options == request.options

        assert len(time_series.time_series) == 2

        # all were requested
        for ts in time_series.time_series:
            assert ts.device_id in request.device_ids
            assert ts.measure_id in request.measure_ids
            assert len(ts.values) == 1

            assert ts.values[0].timestamp == dateutil.parser.parse(
                "2020-01-01T00:00:00"
            )
            assert ts.values[0].value == 25.0

        # all requested were returned
        returned = [(ts.device_id, ts.measure_id) for ts in time_series.time_series]
        assert ("device_1", "tmp") in returned
        assert ("device_2", "tmp") in returned

    def test_scope_selection(self, mock_db: MockDb):
        """
        Test that the scope is correctly selected.
        Tenants cannot be tested because they depend on the database squemas,
        and sqlite does not support multiple schemas.
        """

        cm = mock_db.get_connection_manager()
        session = cm.get_session()

        # insert random devices
        device = DeviceTableModel(
            entity_id=f"device_1",
            entity_type="device",
            time_index=dateutil.parser.parse("2020-01-01T00:00:00Z"),
            fiware_servicepath="/",
            original_ngsi_entity={},
            instance_id="device",
            name_col=f"device_1",
            tmp_col=25.0,
            active_col=True,
            location_col={},
        )

        session.add(device)
        mock_db.update_ds_entity_tables(
            Entity(
                tenant="",
                scope="/",
                urn=f"device_1",
            )
        )

        device = DeviceTableModel(
            entity_id=f"device_2",
            entity_type="device",
            time_index=dateutil.parser.parse("2020-01-01T00:00:00Z"),
            fiware_servicepath="/s1",
            original_ngsi_entity={},
            instance_id="device",
            name_col=f"device_2",
            tmp_col=25.0,
            active_col=True,
            location_col={},
        )

        session.add(device)
        mock_db.update_ds_entity_tables(
            Entity(
                tenant="",
                scope="/s1",
                urn=f"device_2",
            )
        )

        session.commit()

        request = TimeSeriesRequest(
            device_ids=["device_1", "device_2"],
            measure_ids=["tmp"],
            options=TimeSeriesOptions(
                tenant="",
                scope="/",
            ),
        )

        # get the data source
        ds = mock_db.get_ql_ds()

        # get the time series
        time_series = ds.get_single_timeseries_request(request)

        assert time_series.options == request.options

        assert len(time_series.time_series) == 1

        assert time_series.time_series[0].device_id == "device_1"
        assert time_series.time_series[0].measure_id == "tmp"
        assert len(time_series.time_series[0].values) == 1
        assert time_series.time_series[0].values[0].timestamp == dateutil.parser.parse(
            "2020-01-01T00:00:00"
        )
        assert time_series.time_series[0].values[0].value == 25.0

    def test_basic_timeseries_options(self, mock_db: MockDb):
        """
        Test the following options:
        - start_date
        - end_date
        - order
        - limit
        """

        cm = mock_db.get_connection_manager()
        session = cm.get_session()

        self.add_one_year(mock_db, "device_1", 2020)

        # 5 days of data
        start_date = dateutil.parser.parse("2020-01-01T00:00:00Z")
        end_date = dateutil.parser.parse("2020-01-05T00:00:00Z")

        request = TimeSeriesRequest(
            device_ids=["device_1", "device_2"],
            measure_ids=["tmp", "active"],
            options=TimeSeriesOptions(
                tenant="t1",
                scope="/",
                start_date=start_date,
                end_date=end_date,
                order="asc",
                limit=500,
            ),
        )

        # get the data source
        ds = mock_db.get_ql_ds()

        # get the time series
        time_series = ds.get_single_timeseries_request(request)

        assert time_series.options == request.options

        # 5 days of data for 2 measures = 10 time series
        assert len(time_series.time_series) == 2
        assert len(time_series.time_series[0].values) == 5
        assert len(time_series.time_series[1].values) == 5
        for i in range(5):
            assert time_series.time_series[0].values[
                i
            ].timestamp == dateutil.parser.parse(f"2020-01-0{i+1}T00:00:00")
            assert time_series.time_series[0].values[i].value == i

            assert time_series.time_series[1].values[
                i
            ].timestamp == dateutil.parser.parse(f"2020-01-0{i+1}T00:00:00")
            assert time_series.time_series[1].values[i].value == (i % 2 == 0)

        # now descending
        request.options.order = TimeSeriesOrdering.DESC
        time_series = ds.get_single_timeseries_request(request)
        assert time_series.options == request.options
        assert len(time_series.time_series) == 2
        assert len(time_series.time_series[0].values) == 5
        assert len(time_series.time_series[1].values) == 5
        for i in range(5):
            assert time_series.time_series[0].values[
                i
            ].timestamp == dateutil.parser.parse(f"2020-01-0{5-i}T00:00:00")
            assert time_series.time_series[0].values[i].value == 4 - i

            assert time_series.time_series[1].values[
                i
            ].timestamp == dateutil.parser.parse(f"2020-01-0{5-i}T00:00:00")
            assert time_series.time_series[1].values[i].value == ((4 - i) % 2 == 0)

        # check limit is working
        request.options.limit = 3
        time_series = ds.get_single_timeseries_request(request)
        assert time_series.options == request.options
        assert len(time_series.time_series) == 2
        assert len(time_series.time_series[0].values) == 3
        assert len(time_series.time_series[1].values) == 3
        for i in range(3):
            assert time_series.time_series[0].values[
                i
            ].timestamp == dateutil.parser.parse(f"2020-01-0{5-i}T00:00:00")
            assert time_series.time_series[0].values[i].value == 4 - i

            assert time_series.time_series[1].values[
                i
            ].timestamp == dateutil.parser.parse(f"2020-01-0{5-i}T00:00:00")
            assert time_series.time_series[1].values[i].value == ((4 - i) % 2 == 0)

        request.options.order = TimeSeriesOrdering.ASC
        time_series = ds.get_single_timeseries_request(request)
        assert time_series.options == request.options
        assert len(time_series.time_series) == 2
        assert len(time_series.time_series[0].values) == 3
        assert len(time_series.time_series[1].values) == 3
        for i in range(3):
            assert time_series.time_series[0].values[
                i
            ].timestamp == dateutil.parser.parse(f"2020-01-0{i+1}T00:00:00")
            assert time_series.time_series[0].values[i].value == i

            assert time_series.time_series[1].values[
                i
            ].timestamp == dateutil.parser.parse(f"2020-01-0{i+1}T00:00:00")
            assert time_series.time_series[1].values[i].value == (i % 2 == 0)

    def test_where_condition(self, mock_db: MockDb):
        """
        Test the where condition
        """

        cm = mock_db.get_connection_manager()
        session = cm.get_session()

        # 10 devices with the same tmp
        for i in range(10):
            device = DeviceTableModel(
                entity_id=f"device_{i}",
                entity_type="device",
                time_index=dateutil.parser.parse("2020-01-01T00:00:00Z"),
                fiware_servicepath="/",
                original_ngsi_entity={},
                instance_id="device",
                name_col=f"device_{i}",
                tmp_col=25.0,
                active_col=(i % 2 == 0),
                location_col={},
            )

            session.add(device)
            mock_db.update_ds_entity_tables(
                Entity(
                    tenant="t1",
                    scope="/",
                    urn=f"device_{i}",
                )
            )

        mock_db.update_ds_tenant_tables("t1")

        session.commit()

        request = TimeSeriesRequest(
            device_ids=[],
            measure_ids=["name", "tmp"],
            options=TimeSeriesOptions(
                tenant="t1",
                scope="/",
                where=WhereClause(conditions=[("active", "=", True)]),
            ),
        )

        # get the data source
        ds = mock_db.get_ql_ds()

        # get the time series
        time_series = ds.get_single_timeseries_request(request)

        assert time_series.options == request.options
        # only 5 devices are active
        assert len(time_series.time_series) == 10
        assert len(set([ts.device_id for ts in time_series.time_series])) == 5

        # all of them with only one value
        for ts in time_series.time_series:
            assert len(ts.values) == 1
            assert ts.values[0].timestamp == dateutil.parser.parse(
                "2020-01-01T00:00:00"
            )

            if ts.measure_id == "name":
                assert ts.values[0].value == ts.device_id

            if ts.measure_id == "tmp":
                assert ts.values[0].value == 25.0

    def test_month_period_filtering(self, mock_db: MockDb):
        """
        Test the month filtering
        """
        self.add_one_year(mock_db, "device_1", 2020)

        request = TimeSeriesRequest(
            device_ids=["device_1"],
            measure_ids=["tmp"],
            options=TimeSeriesOptions(
                tenant="t1",
                order=TimeSeriesOrdering.ASC,
                scope="/",
                limit=500,
                period=[TimeScope(months=[0])],
            ),
        )

        # get the data source
        ds = mock_db.get_ql_ds()

        # get the time series
        time_series = ds.get_single_timeseries_request(request)

        assert time_series.options == request.options

        # 31 days of data
        assert len(time_series.time_series) == 1
        assert len(time_series.time_series[0].values) == 31

        for i in range(31):
            assert time_series.time_series[0].values[
                i
            ].timestamp == dateutil.parser.parse(f"2020-01-{i+1}T00:00:00")
            assert time_series.time_series[0].values[i].value == i

    def test_month_day_period_filtering(self, mock_db: MockDb):
        """
        Test the month day filtering
        """
        self.add_one_year(mock_db, "device_1", 2020)

        request = TimeSeriesRequest(
            device_ids=["device_1"],
            measure_ids=["tmp"],
            options=TimeSeriesOptions(
                tenant="t1",
                order=TimeSeriesOrdering.ASC,
                scope="/",
                limit=500,
                period=[TimeScope(month_days=[0])],
            ),
        )

        # get the data source
        ds = mock_db.get_ql_ds()

        # get the time series
        time_series = ds.get_single_timeseries_request(request)

        assert time_series.options == request.options

        # 12 days of data
        assert len(time_series.time_series) == 1
        assert len(time_series.time_series[0].values) == 12

        for i in range(12):
            expeted_date = dateutil.parser.parse(f"2020-{i+1}-1T00:00:00")
            assert time_series.time_series[0].values[i].timestamp == expeted_date
            day_of_year = expeted_date.timetuple().tm_yday
            assert time_series.time_series[0].values[i].value == day_of_year - 1

        # now only for the first month
        request.options.period = [TimeScope(month_days=[0], months=[0])]
        time_series = ds.get_single_timeseries_request(request)

        assert time_series.options == request.options

        # 1 day of data
        assert len(time_series.time_series) == 1
        assert len(time_series.time_series[0].values) == 1

        assert time_series.time_series[0].values[0].timestamp == dateutil.parser.parse(
            "2020-01-01T00:00:00"
        )

        assert time_series.time_series[0].values[0].value == 0

    def test_week_day_period_filtering(self, mock_db: MockDb):
        """
        Test the week day filtering
        """

        # 2018 starts on Monday
        self.add_one_year(mock_db, "device_1", 2018)

        request = TimeSeriesRequest(
            device_ids=["device_1"],
            measure_ids=["tmp"],
            options=TimeSeriesOptions(
                tenant="t1",
                order=TimeSeriesOrdering.ASC,
                scope="/",
                limit=500,
                period=[TimeScope(week_days=[0])],
            ),
        )

        # get the data source
        ds = mock_db.get_ql_ds()

        # get the time series
        time_series = ds.get_single_timeseries_request(request)

        assert time_series.options == request.options

        # 52 weeks of data
        assert len(time_series.time_series) == 1
        assert len(time_series.time_series[0].values) == 53

        reference_date = dateutil.parser.parse("2018-01-01T00:00:00")

        for i in range(53):
            day_number = 7 * i
            date = reference_date + dateutil.relativedelta.relativedelta(
                days=day_number
            )

            assert time_series.time_series[0].values[i].timestamp == date

            assert time_series.time_series[0].values[i].value == day_number

    def test_hour_period_filtering(self, mock_db: MockDb):
        """
        Test the hour filtering, with different ranges and mixing them
        with month and month day filtering
        """

        self.add_one_year(mock_db, "device_1", 2020, 1)

        request = TimeSeriesRequest(
            device_ids=["device_1"],
            measure_ids=["tmp"],
            options=TimeSeriesOptions(
                tenant="t1",
                order=TimeSeriesOrdering.ASC,
                scope="/",
                limit=10000,
                period=[
                    TimeScope(hours=[[datetime.time(1, 0, 0), datetime.time(12, 0, 0)]])
                ],
            ),
        )

        # get the data source
        ds = mock_db.get_ql_ds()

        # get the time series
        time_series = ds.get_single_timeseries_request(request)

        assert time_series.options == request.options

        # 12 data points per day
        assert len(time_series.time_series) == 1
        assert len(time_series.time_series[0].values) == 12 * 365

        reference_date = dateutil.parser.parse("2020-01-01T01:00:00")

        for i in range(365):

            for j in range(12):
                date = reference_date + dateutil.relativedelta.relativedelta(hours=j)
                num_hour = i * 24 + j + 1
                assert time_series.time_series[0].values[i * 12 + j].timestamp == date
                assert time_series.time_series[0].values[i * 12 + j].value == num_hour

            reference_date = reference_date + dateutil.relativedelta.relativedelta(
                days=1
            )

        # lets test with a different range
        request.options.period[0].hours = [
            [datetime.time(23, 0, 0), datetime.time(1, 0, 0)]
        ]

        time_series = ds.get_single_timeseries_request(request)

        assert time_series.options == request.options

        # 3 data points per day
        assert len(time_series.time_series) == 1
        assert len(time_series.time_series[0].values) == 3 * 365

        reference_date = dateutil.parser.parse("2020-01-01T1:00:00")

        # in this case, check that all are in the range
        for i in time_series.time_series[0].values:
            assert i.timestamp.time() >= datetime.time(
                23, 0, 0
            ) or i.timestamp.time() <= datetime.time(1, 0, 0)

        # now, only for the first day of the year
        request.options.period[0].months = [0]
        request.options.period[0].month_days = [0]

        time_series = ds.get_single_timeseries_request(request)

        assert time_series.options == request.options

        # 3 data points per day
        assert len(time_series.time_series) == 1
        assert len(time_series.time_series[0].values) == 3

        reference_date = dateutil.parser.parse("2020-01-01T1:00:00")

        # in this case, check that all are in the range
        for i in time_series.time_series[0].values:
            assert i.timestamp.time() >= datetime.time(
                23, 0, 0
            ) or i.timestamp.time() <= datetime.time(1, 0, 0)

        # now mixing two time ranges
        request.options.period[0].hours = [
            [datetime.time(23, 0, 0), datetime.time(1, 0, 0)],
            [datetime.time(1, 0, 0), datetime.time(23, 0, 0)],
        ]

        time_series = ds.get_single_timeseries_request(request)

        assert time_series.options == request.options

        # 24 data points per day, but only on the first day of the year
        assert len(time_series.time_series) == 1
        assert len(time_series.time_series[0].values) == 24

        reference_date = dateutil.parser.parse("2020-01-01T0:00:00")

        for i in range(24):
            date = reference_date + dateutil.relativedelta.relativedelta(hours=i)
            assert time_series.time_series[0].values[i].timestamp == date
            assert time_series.time_series[0].values[i].value == i

    def test_extra_period_filtering(self, mock_db: MockDb):
        """
        Test the extra period filtering, mixed with the other filters
        (otherwise, it does not make sense)
        """

        # one year data
        self.add_one_year(mock_db, "device_1", 2020)

        request = TimeSeriesRequest(
            device_ids=["device_1"],
            measure_ids=["tmp"],
            options=TimeSeriesOptions(
                tenant="t1",
                order=TimeSeriesOrdering.ASC,
                scope="/",
                limit=10000,
                period=[
                    TimeScope(
                        months=[0],
                        extra=[TimeScopeAdjustment(month=1, exclude=False)],
                    )
                ],
            ),
        )

        # get the data source
        ds = mock_db.get_ql_ds()

        # get the time series
        time_series = ds.get_single_timeseries_request(request)

        assert time_series.options == request.options

        # 31 days of data + 29 of February
        assert len(time_series.time_series) == 1
        assert len(time_series.time_series[0].values) == 31 + 29

        reference_date = dateutil.parser.parse("2020-01-01T00:00:00")

        for i in range(31 + 29):

            date = reference_date + dateutil.relativedelta.relativedelta(days=i)

            assert time_series.time_series[0].values[i].timestamp == date

            assert time_series.time_series[0].values[i].value == i

        # now exclude the first month
        request.options.period[0].extra[0].exclude = True
        request.options.period[0].extra[0].month = 0

        time_series = ds.get_single_timeseries_request(request)

        assert time_series.options == request.options

        # no data should be returned
        assert len(time_series.time_series) == 0

        # now include the second month
        request.options.period[0].extra.append(
            TimeScopeAdjustment(month=1, exclude=False)
        )

        time_series = ds.get_single_timeseries_request(request)

        assert time_series.options == request.options

        # 29 days of data
        assert len(time_series.time_series) == 1
        assert len(time_series.time_series[0].values) == 29

        reference_date = dateutil.parser.parse("2020-02-01T00:00:00")

        for i in range(29):

            date = reference_date + dateutil.relativedelta.relativedelta(days=i)

            assert time_series.time_series[0].values[i].timestamp == date

            assert time_series.time_series[0].values[i].value == i + 31
