from typing import Dict, List, Tuple
from app.core.configurable_service.configurable_service import ServiceParamDescription
from app.core.time_series.data_sources.data_source import DataSource
from app.core.time_series.data_sources.quantum_leap.connection_manager import (
    ConnectionManager,
)
from app.core.time_series.data_sources.quantum_leap.schemas.table_schema import (
    TableSchema,
)
from aether_pylib.time_series.time_series import TimeSeries, TimeSeriesValue
from aether_pylib.time_series.time_series_options import (
    TimeSeriesOptions,
    TimeSeriesOrdering,
)
from aether_pylib.time_series.time_series_request import TimeSeriesRequest
from aether_pylib.time_series.time_series_response import TimeSeriesResponse
from app.core.time_series.data_sources.quantum_leap.db_settings import DBSettings
from app.core.time_series.data_sources.quantum_leap.models.md_ets_metadata import (
    MdEtsMetadata,
)
from app.core.time_series.data_sources.quantum_leap.schemas.entity_schema import Entity
from sqlalchemy.orm import Session
from sqlalchemy import Table
import app.core.time_series.data_sources.quantum_leap.query.entity_search as entity_search
import app.core.time_series.data_sources.quantum_leap.quantum_leam_constants as ql_constants
import app.core.time_series.data_sources.quantum_leap.models.utils as model_utils
from app.core.config.logging import appLogging as logging
import app.core.time_series.data_sources.quantum_leap.query.timeseries_query as ts_query
import app.core.time_series.aggregations as aggregations


class QuantumLeapDataSource(DataSource):
    """
    QuantumLeap data source
    """

    def __init__(self, **kwargs):
        self.db_settings: DBSettings = DBSettings(
            HOST=kwargs.get("QL_DB_HOST", None),
            PORT=kwargs.get("QL_DB_PORT", None),
            USER=kwargs.get("QL_DB_USER", None),
            PASS=kwargs.get("QL_DB_PASS", None),
            DB=kwargs.get("QL_DB_NAME", None),
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

        self.connection_manager = ConnectionManager(self.db_settings)

    def params_description() -> ServiceParamDescription:
        """
        Description of the needed kwargs
        """
        return {
            "QL_DB_HOST": {
                "description": "Host of the QuantumLeap database",
                "type": str,
                "required": True,
                "default": "",
            },
            "QL_DB_PORT": {
                "description": "Port of the QuantumLeap database",
                "type": int,
                "required": True,
                "default": "",
            },
            "QL_DB_USER": {
                "description": "User of the QuantumLeap database",
                "type": str,
                "required": True,
                "default": "",
            },
            "QL_DB_PASS": {
                "description": "Password",
                "type": str,
                "required": True,
                "default": "",
            },
            "QL_DB_NAME": {
                "description": "Name of the database",
                "type": str,
                "required": True,
                "default": "",
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
        return False

    def __preprocess(self, requests: List[TimeSeriesRequest], session: Session):
        """
        Runs some preprocessing:
            - Get table attr correspondences (mt_ets_metadata)
            - Get entity tables (in which tables the entities are stored)

        The results are cached in the class instance
            - self.table_metadata: Dict[str, Dict]
                - table_name: Column -> ["attr_name", "attr_type"]

            - self.entity_tables: Dict[Entity, str]
                - Entity(tenant, scope, urn): Table
        """
        logging.info("Preprocessing QuantumLeap data source")
        self.table_metadata = model_utils.get_tables_metadata(session)
        logging.info("Table metadata loaded")
        self.entity_tables, self.tenant_tables = self.__get_entity_tables(
            requests, self.table_metadata, session
        )
        logging.info("Entity tables loaded")

    def __get_tenant_tables(
        self, tenant: str, table_metadata: Dict[str, Dict]
    ) -> List[str]:
        """
        Return a list with the tables that belong to the tenant
        """

        return [
            key
            for key in table_metadata.keys()
            if f"{ql_constants.SCHEMA_PREFIX}{tenant}" in key and "_lastdata" not in key
        ]

    def __get_entity_tables(
        self,
        requests: List[TimeSeriesRequest],
        table_metadata: Dict[str, Dict],
        session: Session,
    ) -> Tuple[Dict[Entity, Table], Dict[str, List[Table]]]:
        """
        Return a mapping of the entity to the table name (the table name includes the schema)
        """

        # group entities by tenant to optimize the query
        tenant_entities = {}
        for request in requests:
            if request.options.tenant not in tenant_entities:
                tenant_entities[request.options.tenant] = set()

            tenant_entities[request.options.tenant].update(
                Entity(
                    tenant=request.options.tenant,
                    scope=request.options.scope,
                    urn=device_id,
                )
                for device_id in request.device_ids
            )

        entity_tables = {}
        all_tenant_tables = {tenant: [] for tenant in tenant_entities.keys()}
        for tenant, entities in tenant_entities.items():

            tenant_tables = self.__get_tenant_tables(tenant, table_metadata)
            for full_table_name in tenant_tables:

                table_schema = model_utils.split_table_name(full_table_name)
                this_table_metadata = table_metadata.get(full_table_name, {})
                if not this_table_metadata:
                    logging.error(
                        f"Table {full_table_name} does not have metadata, skipping"
                    )
                    continue

                table_model = model_utils.get_table_model(
                    table_schema=table_schema,
                    engine=self.connection_manager.get_engine(),
                    metadata=self.connection_manager.get_metadata(),
                )

                all_tenant_tables[tenant].append(table_model)

                found_entities = entity_search.filter_in_table(
                    table=table_model,
                    entities=entities,
                    db=session,
                    table_metadata=this_table_metadata,
                )

                for entity in found_entities:
                    entity_tables[entity] = table_model

        return entity_tables, all_tenant_tables

    def get_time_series(self, requests: List[TimeSeriesRequest]) -> TimeSeriesResponse:
        """
        Retrieve time series data
        """
        session = self.connection_manager.get_session()
        try:

            self.__preprocess(requests, session)
            session.close()
            return [self.get_single_timeseries_request(request) for request in requests]

        except Exception as e:
            session.close()
            raise e

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
        time_series = []
        for entity_id in request.device_ids:
            time_series.extend(
                self.get_timeseries_request_for_entity(
                    entity_id, request.measure_ids, request.options
                )
            )

        return TimeSeriesResponse(time_series=time_series, options=request.options)

    def get_where_broad_request(self, request: TimeSeriesRequest) -> TimeSeriesResponse:
        """
        Processes a query reques that has no device_ids, but has a where clause. In the quantum leap
        structure, there is no other choice than to query all the tables corresponding to the
        tenant and filter the results.
        """

        time_series = []

        tenant_tables = self.tenant_tables.get(request.options.tenant, None)
        if not tenant_tables:
            return TimeSeriesResponse(time_series=[], options=request.options)

        for table_model in tenant_tables:
            time_series.extend(
                self.get_timeseries_request_for_entity(
                    None,
                    request.measure_ids,
                    request.options,
                    target_table=table_model,
                )
            )

        return TimeSeriesResponse(time_series=time_series, options=request.options)

    def get_timeseries_request_for_entity(
        self,
        entity_id: str,
        measure_ids: List[str],
        options: TimeSeriesOptions,
        target_table: Table = None,
    ) -> List[TimeSeries]:
        """
        Retrieve time series data for a single entity
        """

        table_model = (
            target_table
            if target_table is not None
            else self.entity_tables.get(
                Entity(
                    tenant=options.tenant,
                    scope=options.scope,
                    urn=entity_id,
                ),
                None,
            )
        )

        if table_model is None:
            logging.error(f"Table not found for entity {entity_id}, skipping entity")
            return []

        this_table_metadata = self.table_metadata[
            f'"{table_model.schema}"."{table_model.name}"'
        ]

        session = self.connection_manager.get_session()

        try:
            query = ts_query.build_query(
                entity_urn=entity_id,
                attrs=measure_ids,
                options=options,
                table_model=table_model,
                table_metadata=this_table_metadata,
                db=session,
            )

            query_result: List[TimeSeries] = ts_query.execute_query(
                query, measure_ids, this_table_metadata
            )
            session.close()

        except Exception as e:
            session.close()
            raise e

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
