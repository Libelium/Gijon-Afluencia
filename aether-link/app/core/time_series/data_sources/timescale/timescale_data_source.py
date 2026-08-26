import time
from typing import List

from sqlalchemy import select, text
from app.core.time_series.data_sources.data_source import DataSource
from app.core.time_series.data_sources.timescale.connection_manager import (
    ConnectionManager,
)
from app.core.time_series.data_sources.timescale.db_settings import DBSettings
from app.core.configurable_service.configurable_service import ServiceParamDescription
from aether_pylib.time_series.time_series_request import TimeSeriesRequest
from aether_pylib.time_series.time_series_response import TimeSeriesResponse
from aether_pylib.time_series.time_series_hash_response import (
    TimeSeriesHashResponse,
)
from aether_pylib.time_series.delete_time_series_request import (
    DeleteTimeSeriesRequest,
)
from aether_pylib.time_series.delete_time_series_response import (
    DeleteTimeSeriesResponse,
)
from aether_pylib.time_series.deleted_time_series import DeletedTimeSeries
import app.core.time_series.data_sources.timescale.query.query_builder as ts_qb
import app.core.time_series.data_sources.timescale.query.query_parser as ts_qp
import app.core.time_series.data_sources.timescale.query.timeseries_hash_query as ts_hash
from app.core.config.logging import appLogging as logging
from fastapi import HTTPException
from sqlalchemy.orm import Session


class TimescaleDatasource(DataSource):
    """
    QuantumLeap data source
    """

    def __init__(self, **kwargs):
        self.db_settings: DBSettings = DBSettings(
            HOST=kwargs.get("PLATFORM_TS_DB_HOST", None),
            PORT=kwargs.get("PLATFORM_TS_DB_PORT", None),
            USER=kwargs.get("PLATFORM_TS_DB_USER", None),
            PASS=kwargs.get("PLATFORM_TS_DB_PASS", None),
            DB=kwargs.get("PLATFORM_TS_DB_NAME", None),
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
        # First call to the hash endpoint per pod lifetime ensures pgcrypto is
        # available; we cache the success flag so subsequent requests skip the
        # DDL roundtrip.
        self._pgcrypto_ready: bool = False

    def params_description() -> ServiceParamDescription:
        """
        Description of the needed kwargs
        """
        return {
            "PLATFORM_TS_DB_HOST": {
                "description": "Host of the Timescale database",
                "type": str,
                "required": True,
                "default": "",
            },
            "PLATFORM_TS_DB_PORT": {
                "description": "Port of the Timescale database",
                "type": int,
                "required": True,
                "default": "",
            },
            "PLATFORM_TS_DB_USER": {
                "description": "User of the Timescale database",
                "type": str,
                "required": True,
                "default": "",
            },
            "PLATFORM_TS_DB_PASS": {
                "description": "Password",
                "type": str,
                "required": True,
                "default": "",
            },
            "PLATFORM_TS_DB_NAME": {
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

    def health_check(self):
        db = next(self.connection_manager.get_session())
        try:
            db.execute(text("SELECT 1"))
            db.close()
        except Exception as e:
            logging.error(f"Error executing health check query: {e}")
            return False

        return True

    def get_time_series(self, requests: List[TimeSeriesRequest]) -> TimeSeriesResponse:
        """
        Retrieve time series data from the data source for the given requests. The behavior
        must match the TimeSeriesRequest specification
        """
        return [self.get_single_time_series(request) for request in requests]

    def get_single_time_series(self, request: TimeSeriesRequest) -> TimeSeriesResponse:
        """
        Retrieve time series data from the data source for the given request. The behavior
        must match the TimeSeriesRequest specification
        """

        db: Session = next(self.connection_manager.get_session())

        query = ts_qb.build_query(
            request,
            self.connection_manager.metadata,
        )

        try:

            # log payload
            logging.info(f"Payload received: {request}")
            # log query
            logging.info(
                f"Executing query: {query.compile(compile_kwargs={'literal_binds': True})}"
            )
            # log query time execution
            start_time = time.time()
            query_result = db.execute(query).fetchall()
            end_time = time.time()
            logging.info(f"Query execution time: {end_time - start_time} seconds")
            db.close()

        except Exception as e:
            logging.error(f"Error executing query: {e}")
            return TimeSeriesResponse(
                time_series=[],
                options=request.options,
            )

        columns = {c["name"]: i for i, c in enumerate(query.column_descriptions)}

        time_series = ts_qp.to_timeseries_schema(query_result, columns)

        return TimeSeriesResponse(
            time_series=time_series,
            options=request.options,
        )

    def get_time_series_hash(
        self, requests: List[TimeSeriesRequest]
    ) -> List[TimeSeriesHashResponse]:
        """
        Compute a deterministic sha256 digest of each request's underlying rows
        directly inside Postgres (pgcrypto). One TimeSeriesHashResponse per
        request element, in the same order.
        """
        return [self.__hash_single_request(request) for request in requests]

    def __ensure_pgcrypto(self, db: Session) -> None:
        if self._pgcrypto_ready:
            return
        db.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
        db.commit()
        self._pgcrypto_ready = True
        logging.info("pgcrypto extension ensured on the platform timescale DB")

    def __hash_single_request(
        self, request: TimeSeriesRequest
    ) -> TimeSeriesHashResponse:
        if request.options.aggregation:
            raise HTTPException(
                status_code=400,
                detail="The hash endpoint does not support aggregation",
            )

        db: Session = next(self.connection_manager.get_session())

        try:
            self.__ensure_pgcrypto(db)
            data_hash, row_count = ts_hash.execute_hash_query(
                session=db,
                tenant=request.options.tenant,
                scope=request.options.scope,
                entity_ids=request.device_ids or [],
                attr_ids=request.measure_ids or [],
                start_date=request.options.start_date,
                end_date=request.options.end_date,
            )
        except HTTPException:
            raise
        except Exception as e:
            logging.error(f"Error executing hash query: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error executing time series hash query: {e}",
            )
        finally:
            db.close()

        return TimeSeriesHashResponse(
            tenant=request.options.tenant,
            scope=getattr(request.options, "scope", None),
            entity_ids=[str(d) for d in (request.device_ids or [])],
            measure_ids=request.measure_ids or [],
            start_date=request.options.start_date,
            end_date=request.options.end_date,
            row_count=row_count,
            algorithm="sha256",
            data_hash=data_hash,
        )

    def delete_time_series(
        self, requests: List[DeleteTimeSeriesRequest]
    ) -> List[DeleteTimeSeriesResponse]:
        """
        Delete time series data from the data source for the given requests. The behavior
        must match the DeleteTimeSeriesRequest specification
        """
        return [self.delete_single_time_series(request) for request in requests]

    def delete_single_time_series(
        self, request: DeleteTimeSeriesRequest
    ) -> DeleteTimeSeriesResponse:
        """
        Delete time series data from the data source for the given request. The behavior
        must match the DeleteTimeSeriesRequest specification
        """
        db: Session = next(self.connection_manager.get_session())

        query = ts_qb.build_delete_query(
            request,
            self.connection_manager.metadata,
        )

        try:
            # log payload
            logging.info(f"Delete Payload received: {request}")
            # log query
            logging.info(
                f"Executing delete query: {query.compile(compile_kwargs={'literal_binds': True})}"
            )
            # log query time execution
            start_time = time.time()

            db.execute(query)
            db.commit()  # Commit the transaction
            end_time = time.time()
            logging.info(
                f"Delete query execution time: {end_time - start_time} seconds"
            )
        except Exception as e:
            db.rollback()  # Rollback on error
            logging.error(f"Error executing delete query: {e}")
            db.close()
            return DeleteTimeSeriesResponse(
                deleted_time_series=[],
                options=request.options,
            )

        db.close()

        # Prepare the response with the deleted time series
        deleted_time_series_list = [
            DeletedTimeSeries(device_id=device_id, measure_id=measure_id)
            for device_id in request.device_ids
            for measure_id in request.measure_ids
        ]

        return DeleteTimeSeriesResponse(
            deleted_time_series=deleted_time_series_list,
            options=request.options,
        )
