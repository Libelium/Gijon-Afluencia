from typing import List, Optional

from config.logging import appLogging as logging
from db.session_helpers import main_session
from jobs.alarms.alarm.alarm_factory import AlarmFactory
from jobs.job import Job
from schemas.entity_data_notification import (
    EntityAttrType,
    EntityDataNotification,
)
from sqlalchemy.orm import Session


class AlarmsJob(Job):
    """
    Evalua las alarmas de umbral que pueden dispararse o rearmarse con los
    valores que acaba de reportar una entidad.
    """

    def __init__(
        self,
        entity_data: EntityDataNotification,
        db: Optional[Session] = None,
    ):
        self.entity_data = entity_data
        self._injected_db = db

    def handle(self) -> None:
        logging.info(f"Handling AlarmsJob job: {self.entity_data.urn}")

        with main_session(self._injected_db) as db:
            alarms = AlarmFactory().get_alarms(
                self.__get_related_measures(),
                self.entity_data,
                db,
            )

            for alarm in alarms:
                try:
                    alarm.update()

                except Exception as e:
                    logging.error(f"Error actualizando una alarma de umbral: {e}")

    def __get_related_measures(self) -> List[str]:
        """
        Medidas que trae la notificacion. Los comandos no cuentan: no son datos
        reportados por la entidad.
        """
        return [
            attr.name
            for attr in self.entity_data.data
            if attr.type != EntityAttrType.COMMAND
        ]
