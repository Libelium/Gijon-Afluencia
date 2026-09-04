from datetime import datetime
from typing import Optional

from config.logging import appLogging as logging
from db.session_helpers import main_session, realtime_session
from jobs.alarms.alarm.alarm_factory import AlarmFactory
from jobs.job import Job
from sqlalchemy.orm import Session


class InactivityAlarmsJob(Job):
    """
    Repasa todas las alarmas de inactividad y actualiza su estado. Esta pensado
    para ejecutarse periodicamente: nadie notifica que un dato NO ha llegado.
    """

    def __init__(
        self,
        current_time: Optional[datetime] = None,
        db: Optional[Session] = None,
        realtime_db: Optional[Session] = None,
    ):
        self.current_time = current_time
        self._injected_db = db
        self._injected_realtime = realtime_db

    def handle(self) -> None:
        logging.info("Handling InactivityAlarmsJob job")

        # Todas las alarmas de la pasada se evaluan con el mismo instante.
        current_time = self.current_time or datetime.now()

        with main_session(self._injected_db) as db, realtime_session(
            self._injected_realtime
        ) as realtime_db:
            alarms = AlarmFactory().get_inactivity_alarms(
                current_time=current_time,
                db=db,
                realtime_db=realtime_db,
            )

            for alarm in alarms:
                try:
                    alarm.update()

                except Exception as e:
                    logging.error(
                        f"Error actualizando una alarma de inactividad: {e}"
                    )
