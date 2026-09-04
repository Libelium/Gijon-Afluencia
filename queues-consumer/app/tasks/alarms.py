import os
from datetime import datetime

from config.celery import DEFAULT_TASK_ARGS
from config.celery import app as celery_app
from config.config import settings
from config.logging import appLogging as logging
from config.queues import (
    ALARMS_CHECK_INACTIVITY_QUEUE_NAME,
    ALARMS_ENTITY_DATA_CHECK_QUEUE_NAME,
)
from db.session_helpers import main_session
from jobs.alarms.alarms_job import AlarmsJob
from jobs.alarms.inactivity_alarms_job import InactivityAlarmsJob
from models.crud.crud_etl_executions import (
    create_etl_execution,
    get_etl_execution_with_specific_params,
)
from schemas.entity_data_notification import EntityDataNotification

# Cada cuanto se repasan las alarmas de inactividad, en segundos.
INACTIVITY_ALARM_CHECK_INTERVAL = int(
    os.getenv("INACTIVITY_ALARM_CHECK_INTERVAL", 60 * 60)
)


@celery_app.task(
    name="platform.alarms.alarms_job",
    queue=ALARMS_ENTITY_DATA_CHECK_QUEUE_NAME,
    **DEFAULT_TASK_ARGS,
    time_limit=settings.QUEUE_TASK_CONFIG.get_config_param(
        ALARMS_ENTITY_DATA_CHECK_QUEUE_NAME, "timeout"
    ),
)
def alarms_job(self, entity_data: EntityDataNotification) -> None:
    """
    Evalua las alarmas de umbral afectadas por los datos de una entidad.
    """
    AlarmsJob(entity_data=entity_data).handle()


@celery_app.task(
    name="platform.alarms.check_inactivity_alarms",
    queue=ALARMS_CHECK_INACTIVITY_QUEUE_NAME,
    **DEFAULT_TASK_ARGS,
    time_limit=settings.QUEUE_TASK_CONFIG.get_config_param(
        ALARMS_CHECK_INACTIVITY_QUEUE_NAME, "timeout"
    ),
)
def check_inactivity_alarms(self, date: str = None, force: bool = False) -> None:
    """
    Repasa las alarmas de inactividad. La ejecucion queda registrada por hora
    para que dos programadores solapados no la repitan; `force` la repite a
    proposito.
    """
    now = datetime.fromisoformat(date) if date else datetime.now()
    # La clave del ETL se trunca a la hora para deduplicar la pasada, pero las alarmas
    # se evaluan con el instante real: el intervalo de beat no cae en hora en punto.
    params = {"date": now.replace(minute=0, second=0, microsecond=0).isoformat()}

    with main_session() as db:
        previous_execution = get_etl_execution_with_specific_params(
            db,
            etl_type=ALARMS_CHECK_INACTIVITY_QUEUE_NAME,
            params=params,
        )

        if previous_execution and not force:
            logging.info(
                f"Las alarmas de inactividad ya se repasaron con {params}: se omite"
            )
            return

        if not previous_execution:
            create_etl_execution(
                db,
                ALARMS_CHECK_INACTIVITY_QUEUE_NAME,
                params=params,
            )

    InactivityAlarmsJob(current_time=now).handle()


@celery_app.on_after_finalize.connect
def setup_periodic_alarm_tasks(sender, **kwargs):
    logging.info("Setting up periodic inactivity alarm task")
    sender.add_periodic_task(
        INACTIVITY_ALARM_CHECK_INTERVAL,
        check_inactivity_alarms.s(),
        name="Check inactivity alarms",
    )
