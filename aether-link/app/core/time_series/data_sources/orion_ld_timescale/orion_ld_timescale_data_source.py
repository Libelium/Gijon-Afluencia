from typing import Dict, List, Tuple
from app.core.configurable_service.configurable_service import ServiceParamDescription
from app.core.time_series.data_sources.data_source import DataSource
from app.core.time_series.data_sources.orion_ld_timescale.connection_manager import (
    ConnectionManager,
)
from aether_pylib.time_series.time_series import TimeSeries
from aether_pylib.time_series.time_series_options import (
    TimeSeriesOptions,
    TimeSeriesOrdering,
)
from aether_pylib.time_series.time_series_request import TimeSeriesRequest
from aether_pylib.time_series.time_series_response import TimeSeriesResponse
from app.core.time_series.data_sources.orion_ld_timescale.db_settings import DBSettings
from sqlalchemy.orm import Session
from sqlalchemy import Table
from app.core.config.logging import appLogging as logging
import app.core.time_series.data_sources.orion_ld_timescale.query.timeseries_query as ts_query
import app.core.time_series.aggregations as aggregations
from app.core.time_series.data_sources.orion_ld_timescale.orion_ld_timescale_constants import DATABASE_PREFIX

class OrionLDTimescaleDataSource(DataSource):
    """
    OrionLDTimescale data source
    """

    def __init__(self, **kwargs):
        self.db_settings: DBSettings = DBSettings(
            HOST=kwargs.get("ORION_LD_TIMESCALE_HOST", None),
            PORT=kwargs.get("ORION_LD_TIMESCALE_PORT", None),
            USER=kwargs.get("ORION_LD_TIMESCALE_USER", None),
            PASS=kwargs.get("ORION_LD_TIMESCALE_PASSWORD", None),
            DB=kwargs.get("ORION_LD_TIMESCALE_DB_NAME_PREFIX", None),
            POOL_SIZE=kwargs.get("GUNICORN_WORKERS", 10),
        )

        # Check if all the required parameters are present,
        # this is a double check, the ConfigurableService should
        # have already checked this
        if (
            not self.db_settings.HOST
            or not self.db_settings.PORT
            or not self.db_settings.USER
            or not self.db_settings.PASS
            or not self.db_settings.DB
        ):
            raise ValueError("Not all required parameters were provided")

        # self.connection_manager = ConnectionManager(self.db_settings)

    def params_description() -> ServiceParamDescription:
        """
        Description of the needed kwargs
        """
        return {
            "ORION_LD_TIMESCALE_HOST": {
                "description": "Host of the OrionLDTimescale database",
                "type": str,
                "required": True,
                "default": "",
            },
            "ORION_LD_TIMESCALE_PORT": {
                "description": "Port of the OrionLDTimescale database",
                "type": int,
                "required": True,
                "default": "",
            },
            "ORION_LD_TIMESCALE_USER": {
                "description": "User of the OrionLDTimescale database",
                "type": str,
                "required": True,
                "default": "",
            },
            "ORION_LD_TIMESCALE_PASSWORD": {
                "description": "Password",
                "type": str,
                "required": True,
                "default": "",
            },
            "ORION_LD_TIMESCALE_DB_NAME_PREFIX": {
                "description": "Prexix name of the database",
                "type": str,
                "required": True,
                "default": "orion",
            },
            "GUNICORN_WORKERS": {
                "description": "Pool size",
                "type": int,
                "required": True,
                "default": 0,
            },
        }

    def health_check(self) -> bool:
        """
        Check if the data source is healthy
        """
        return False # TODO: CHECK THIS

    def get_time_series(self, requests: List[TimeSeriesRequest]) -> TimeSeriesResponse:
        """
        Retrieve time series data
        """
        # get all the db connections
        self.__get_all_db_connections(requests)

        result = [self.get_single_timeseries_request(request) for request in requests]

        [connection.close() for connection in self.db_connections.values()]

        return result

    def __get_all_db_connections(self, request: List[TimeSeriesRequest]) -> Dict[str, Session]:
        # get all the tenants (uniques)
        tenants = []
        for req in request:
            tenants.append(req.options.tenant)
            
        tenants = list(set(tenants))
        
        # create a connection for each tenant
        db_connections = {}
        for tenant in tenants:
            self.db_settings.DB = f"{DATABASE_PREFIX}_{tenant}"
            db_connections[tenant] = ConnectionManager(self.db_settings)
            
        self.db_connections = db_connections

    def get_single_timeseries_request(
        self, request: TimeSeriesRequest
    ) -> TimeSeriesResponse:
        """
        Retrieve time series data for a single request
        """
        # if no device_ids are provided, there must be a where clause
        if not request.device_ids and not request.options.where:
            raise ValueError(
                "Neither device_ids nor where clause are provided. At least one of them must be provided"
            )

        if not request.device_ids:
            return self.get_where_broad_request(request)

        else:
            return self.get_multientity_request(request)

    def get_multientity_request(self, request: TimeSeriesRequest) -> TimeSeriesResponse:
        """
        Processes a query request that has multiple device_ids and possibly a where
        clause.
        """
        # normal query for multiple entities
        time_series = self.get_timeseries_request_for_entity(
            request.device_ids, request.measure_ids, request.options
        )

        return TimeSeriesResponse(time_series=time_series, options=request.options)

    def get_where_broad_request(self, request: TimeSeriesRequest) -> TimeSeriesResponse:
        """
        Processes a query reques that has no device_ids, but has a where clause. In the quantum leap
        structure, there is no other choice than to query all the tables corresponding to the
        tenant and filter the results.
        """
        # TODO: NOT IMPLEMENTED

        time_series = []

        return TimeSeriesResponse(time_series=time_series, options=request.options)

    def get_timeseries_request_for_entity(
        self,
        entity_ids: List[str],
        measure_ids: List[str],
        options: TimeSeriesOptions,
    ) -> List[TimeSeries]:
        """
        Retrieve time series data for a single entity
        """
        db_connection = self.db_connections[f"{options.tenant}"]
        
        session = db_connection.get_session()

        query = ts_query.build_query(
            entity_urns=entity_ids,
            attrs=measure_ids,
            options=options,
            db=session,
        )

        query_result: List[TimeSeries] = ts_query.execute_query(
            query,
            entity_ids,
            measure_ids,
            db=session,
        )

        # no aggregation needed
        if not options.aggregation:
            return query_result

        for ts in query_result:
            ts.values = aggregations.aggregate(
                options=options.aggregation,
                values=ts.values,
            )

            if options.order == TimeSeriesOrdering.ASC:
                ts.values.reverse()

        return query_result
