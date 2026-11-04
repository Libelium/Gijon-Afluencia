from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.orm import Session

import models.crud.crud_out_connectors as crud_out_connectors
from config.config import settings
from config.logging import appLogging as logging
from db.session_helpers import main_session, realtime_session
from jobs.job import Job
from jobs.out_connectors.out_connector.factory.out_connector_factory import (
    OutConnectorFactory,
)
from models.crud.crud_log import create_error_log
from models.out_connector_model import OutConnector, OutConnectorStatus
from schemas.entity_data_notification import EntityDataNotification
from schemas.resource_schema import ResourceType


class OutConnectorJob(Job):
    """
    Sends data through one out connector, either one entity notification or (without it)
    the periodic snapshot of the connector, and keeps the connector health: after
    NUM_MAX_RETRIES consecutive failures with no success in the deactivation window,
    the connector is set inactive and stops sending.
    """

    def __init__(
        self,
        out_connector_id: int,
        notification: Optional[EntityDataNotification] = None,
        db: Optional[Session] = None,
        realtime_db: Optional[Session] = None,
    ):
        self.out_connector_id = out_connector_id
        self.notification = notification
        self._injected_main = db
        self._injected_realtime = realtime_db
        self.db: Optional[Session] = None
        self.out_connector_factory = OutConnectorFactory()

    def handle(self) -> None:
        with main_session(self._injected_main) as db, \
                realtime_session(self._injected_realtime) as realtime_db:
            self.db = db

            # Read fresh: the queued copy may be stale (deactivated or deleted meanwhile).
            out_connector = crud_out_connectors.get_out_connector_by_id(
                self.out_connector_id, db
            )
            if out_connector is None or out_connector.status != OutConnectorStatus.ACTIVE:
                logging.info(
                    f"Skipping out connector {self.out_connector_id}: missing or not active"
                )
                return

            logging.info(
                f"Processing out connector with id {out_connector.id} and type {out_connector.type}"
            )

            try:
                sent = self.out_connector_factory.build_out_connector(
                    out_connector=out_connector,
                    entity_data=self.notification,
                    iris_db=db,
                    realtime_db=realtime_db,
                ).handle()
            except Exception as e:
                self.__register_failure(out_connector, e)
                return

            if sent:
                self.__register_success(out_connector)
            else:
                logging.info(f"Out connector {out_connector.id}: nothing to send")

    def __register_success(self, out_connector: OutConnector) -> None:
        if out_connector.retries:
            crud_out_connectors.update_out_connector(
                out_connector.id, {"retries": 0}, self.db
            )

        crud_out_connectors.update_out_connector_last_connection_if_newer(
            out_connector.id, datetime.now(timezone.utc), self.db
        )

    def __register_failure(self, out_connector: OutConnector, error: Exception) -> None:
        logging.error(f"Error processing out connector {out_connector.id}: {error}")
        self.__log_error(out_connector.id, f"Error processing out connector: {error}")

        crud_out_connectors.update_out_connector_retries(out_connector.id, self.db)
        out_connector = crud_out_connectors.get_out_connector_by_id(out_connector.id, self.db)

        if out_connector.retries < settings.NUM_MAX_RETRIES:
            return

        if self.__succeeded_recently(out_connector.last_connection):
            return

        crud_out_connectors.update_out_connector(
            out_connector.id,
            {"status": OutConnectorStatus.INACTIVE.value, "retries": 0},
            self.db,
        )
        logging.warning(f"Out connector {out_connector.id} deactivated after repeated failures")
        self.__log_error(
            out_connector.id,
            f"Out connector deactivated after {settings.NUM_MAX_RETRIES} consecutive failures",
        )

    def __succeeded_recently(self, last_connection: Optional[datetime]) -> bool:
        if last_connection is None:
            return False

        # The column has no time zone and the platform writes it in UTC.
        if last_connection.tzinfo is None:
            last_connection = last_connection.replace(tzinfo=timezone.utc)

        window = timedelta(seconds=settings.CONNECTOR_DEACTIVATION_WINDOW_SECONDS)
        return datetime.now(timezone.utc) - last_connection < window

    def __log_error(self, out_connector_id: int, message: str) -> None:
        create_error_log(
            self.db,
            {
                "datetime": datetime.now(),
                "message": message,
                "extra": {},
                "resource_type": ResourceType.OUT_CONNECTORS,
                "resource_id": out_connector_id,
            },
        )
