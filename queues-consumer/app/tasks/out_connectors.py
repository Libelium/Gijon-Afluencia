from typing import List

from config.celery import DEFAULT_TASK_ARGS
from config.celery import app as celery_app
from config.config import settings
from config.logging import appLogging as logging
from config.queues import OUT_CONNECTOR_QUEUE_NAME
from db.session_helpers import main_session
from jobs.out_connectors.out_connector_job import OutConnectorJob
from models.crud import crud_out_connectors
from models.out_connector_mqtt_model import (
    INVENTORY_PAYLOAD_TYPES,
    READINGS_PAYLOAD_TYPES,
)
from schemas.out_connector_request import OutConnectorRequest

OUT_CONNECTOR_TIMEOUT = settings.QUEUE_TASK_CONFIG.get_config_param(
    OUT_CONNECTOR_QUEUE_NAME, "timeout"
)


@celery_app.task(
    name="platform.out-connector.generic",
    queue=OUT_CONNECTOR_QUEUE_NAME,
    **DEFAULT_TASK_ARGS,
    time_limit=OUT_CONNECTOR_TIMEOUT,
)
def generic_connector_job(self, request: OutConnectorRequest) -> None:
    """
    Sends the notification of an entity through one out connector.
    """
    OutConnectorJob(
        out_connector_id=request.out_connector["id"],
        notification=request.notification,
    ).handle()


@celery_app.task(
    name="platform.out-connector.snapshot",
    queue=OUT_CONNECTOR_QUEUE_NAME,
    **DEFAULT_TASK_ARGS,
    time_limit=OUT_CONNECTOR_TIMEOUT,
)
def snapshot_connector_job(self, out_connector_id: int) -> None:
    """
    Sends the current snapshot of one out connector.
    """
    OutConnectorJob(out_connector_id=out_connector_id).handle()


@celery_app.task(
    name="platform.out-connector.snapshot_all",
    queue=OUT_CONNECTOR_QUEUE_NAME,
    **DEFAULT_TASK_ARGS,
    time_limit=OUT_CONNECTOR_TIMEOUT,
)
def snapshot_connectors_job(self, payload_types: List[str]) -> None:
    """
    Enqueues the snapshot of every active out connector of the given payload types,
    one job each so a slow broker does not hold back the rest.
    """
    with main_session() as db:
        connector_ids = crud_out_connectors.get_active_snapshot_connector_ids(
            payload_types, db
        )

    logging.info(f"Enqueuing snapshot of out connectors {connector_ids} ({payload_types})")
    for connector_id in connector_ids:
        snapshot_connector_job.delay(connector_id)


@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    logging.info("Setting up periodic out connector tasks")
    sender.add_periodic_task(
        settings.OUT_CONNECTOR_READINGS_INTERVAL,
        snapshot_connectors_job.s(list(READINGS_PAYLOAD_TYPES)),
        name="Send out connector readings",
    )
    sender.add_periodic_task(
        settings.OUT_CONNECTOR_INVENTORY_INTERVAL,
        snapshot_connectors_job.s(list(INVENTORY_PAYLOAD_TYPES)),
        name="Send out connector device inventory",
    )
