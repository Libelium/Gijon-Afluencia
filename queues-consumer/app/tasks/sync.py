from sqlite3 import OperationalError
from celery.exceptions import Reject
from config.celery import DEFAULT_TASK_ARGS
from config.celery import app as celery_app
from config.config import settings
from config.logging import appLogging as logging
from config.queues import (
    SYNC_AUTO_SUBSCRIPTION_SYNC_QUEUE_NAME,
    SYNC_CB_NOTIFICATION_QUEUE_NAME,
    SYNC_CB_NOTIFICATION_DLQ_NAME,
    SYNC_NEW_CB_SUBSCRIPTION_QUEUE_NAME,
    SYNC_REALTIME_QUEUE_NAME,
    SYNC_TIMESERIES_QUEUE_NAME,
)
from db.deps import get_db
from db.realtime import get_db_realtime
from jobs.entities.auto_subscription_sync_job import AutoSubscriptionSyncJob
from jobs.realtime.realtime_sync_job import update_entity as update_entity_realtime
from jobs.timeseries.save_timeseries_job import SaveTimeseriesJob
from schemas.auto_subscription_request_schema import AutoSubscriptionRequestSchema
from schemas.context_broker_notification_schema import ContextBrokerNotification
from schemas.fiware_subscription_schema import TypeSubscriptionMessage
from schemas.entity_data_notification import EntityDataNotification


@celery_app.task(
    name="platform.sync.fiware_orion_subscription_job",
    queue=SYNC_CB_NOTIFICATION_QUEUE_NAME,
    **DEFAULT_TASK_ARGS,
    acks_late=True,
    autoretry_for=(Exception,),
    retry_kwargs={
        "max_retries": settings.QUEUE_TASK_CONFIG.get_config_param(
            SYNC_CB_NOTIFICATION_QUEUE_NAME, "max_retries"
        )
    },
    retry_backoff=settings.QUEUE_TASK_CONFIG.get_config_param(
        SYNC_CB_NOTIFICATION_QUEUE_NAME, "retry_backoff"
    ),
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=settings.QUEUE_TASK_CONFIG.get_config_param(
        SYNC_CB_NOTIFICATION_QUEUE_NAME, "timeout"
    ),
)
def fiware_orion_subscription_job(
    self, notification: ContextBrokerNotification
) -> None:
    """
    Process an orion messages.
    If max retries is exceeded, message is moved to Dead Letter Queue.
    """

    try:
        from jobs.sync.entity_sync import EntitySync

        db_session = next(get_db())
        realtime_db_session = next(get_db_realtime())
        job = EntitySync(notification, db=db_session, realtime_db=realtime_db_session)
        job.handle()

    except Exception as e:
        max_retries = settings.QUEUE_TASK_CONFIG.get_config_param(
            SYNC_CB_NOTIFICATION_QUEUE_NAME, "max_retries"
        )

        if self.request.retries >= max_retries:
            logging.error(
                f"Message exhausted retries ({self.request.retries}/{max_retries}), "
                f"moving to DLQ. Task ID: {self.request.id}, "
                f"URN: {_extract_urn_from_notification(notification)}, Error: {str(e)}"
            )

            try:
                celery_app.send_task(
                    "platform.sync.fiware_orion_subscription_job",
                    args=[notification],
                    queue=SYNC_CB_NOTIFICATION_DLQ_NAME,
                )
                logging.info(
                    f"Message successfully moved to DLQ: {SYNC_CB_NOTIFICATION_DLQ_NAME}"
                )
            except Exception as dlq_error:
                logging.error(f"Failed to move message to DLQ: {dlq_error}")

            raise Reject(requeue=False)

        retry_backoff = settings.QUEUE_TASK_CONFIG.get_config_param(
            SYNC_CB_NOTIFICATION_QUEUE_NAME, "retry_backoff"
        )
        logging.warning(
            f"Retrying message ({self.request.retries + 1}/{max_retries}). "
            f"Task ID: {self.request.id}, Error: {str(e)}"
        )
        raise self.retry(
            exc=e,
            countdown=retry_backoff * (2**self.request.retries),
            max_retries=max_retries,
        )


@celery_app.task(
    name="platform.sync.save_timeseries_job",
    queue=SYNC_TIMESERIES_QUEUE_NAME,
    **DEFAULT_TASK_ARGS,
    time_limit=settings.QUEUE_TASK_CONFIG.get_config_param(
        SYNC_TIMESERIES_QUEUE_NAME, "timeout"
    ),
)
def save_timeseries_job(self, entity_data: EntityDataNotification) -> None:
    """
    Process data messages
    """

    job = SaveTimeseriesJob(entity_data)
    job.handle()


@celery_app.task(
    name="platform.sync.save_realtime_job",
    queue=SYNC_REALTIME_QUEUE_NAME,
    **DEFAULT_TASK_ARGS,
    time_limit=settings.QUEUE_TASK_CONFIG.get_config_param(
        SYNC_REALTIME_QUEUE_NAME, "timeout"
    ),
)
def save_realtime_job(self, entity_data: EntityDataNotification) -> None:
    """
    Process data messages to be saved in realtime
    """
    realtime_db = next(get_db_realtime())
    main_db = next(get_db())
    update_entity_realtime(entity_data, realtime_db=realtime_db, main_db=main_db)


@celery_app.task(
    name="platform.sync.fiware_type_subscription_job",
    queue=SYNC_NEW_CB_SUBSCRIPTION_QUEUE_NAME,
    **DEFAULT_TASK_ARGS,
    time_limit=settings.QUEUE_TASK_CONFIG.get_config_param(
        SYNC_NEW_CB_SUBSCRIPTION_QUEUE_NAME, "timeout"
    ),
)
def fiware_type_subscription_job(
    self, type_sub_message: TypeSubscriptionMessage
) -> None:
    """
    Process an orion messages
    """
    from jobs.entities.entities_sync_job import FiwareEntitiesSync

    db_session = next(get_db())
    realtime_db = next(get_db_realtime())
    job = FiwareEntitiesSync(
        type_sub_message, main_db=db_session, realtime_db=realtime_db
    )
    job.handle()


@celery_app.task(
    name="platform.sync.auto_subscription_sync_job",
    queue=SYNC_AUTO_SUBSCRIPTION_SYNC_QUEUE_NAME,
    **DEFAULT_TASK_ARGS,
    time_limit=settings.QUEUE_TASK_CONFIG.get_config_param(
        SYNC_AUTO_SUBSCRIPTION_SYNC_QUEUE_NAME, "timeout"
    ),
)
def auto_subscription_sync_job(
    self, auto_subscription_request: AutoSubscriptionRequestSchema
) -> None:
    main_db = next(get_db())
    job = AutoSubscriptionSyncJob(auto_subscription_request, main_db)
    job.handle()


def _extract_urn_from_notification(notification: ContextBrokerNotification) -> str:
    """
    Helper to extract URN from notification payload for logging.
    Returns 'unknown' if URN cannot be extracted.
    """
    try:
        if hasattr(notification, "body") and isinstance(notification.body, dict):
            data = notification.body.get("data", [])
            if data and len(data) > 0:
                return data[0].get("id", "unknown")
    except Exception:
        pass
    return "unknown"


@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    logging.info("Setting up periodic alarm tasks")
    sender.add_periodic_task(
        settings.AUTO_SYNC_INTERVAL,
        auto_subscription_sync_job.s(AutoSubscriptionRequestSchema(
            organizations=[],
            create_new_subscriptions=True,
        )),
        name="Auto sync subs with context broker",
    )
