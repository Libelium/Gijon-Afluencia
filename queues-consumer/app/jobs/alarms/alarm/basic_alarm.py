from datetime import datetime
from typing import Optional

import jobs.alarms.queries as queries
from config.logging import appLogging as logging
from helpers.iota import iota_helper as iota
from jobs.alarms.action.action_factory import ActionFactory
from jobs.alarms.alarm.alarm import Alarm
from jobs.alarms.alarm_activator.alarm_activator import AlarmActivator
from jobs.alarms.models import Alarm as AlarmModel
from models.crud.crud_log import create_info_log
from schemas.resource_schema import ResourceType
from sqlalchemy.orm import Session


class BasicAlarm(Alarm):
    """
    Alarma de umbral: sus condiciones comparan el ultimo valor de una medida
    con los umbrales configurados.
    """

    def __init__(
        self,
        alarm_model: AlarmModel,
        activator: AlarmActivator,
        db: Session,
        iota_service_apikey: Optional[str] = None,
        iota_service_resource: Optional[str] = None,
    ):
        self.alarm_model = alarm_model
        self.activator = activator
        self.db = db
        self.iota_service_apikey = iota_service_apikey
        self.iota_service_resource = iota_service_resource

    def update(self) -> None:
        logging.info(f"Actualizando la alarma {self.alarm_model.id}")

        alarm_status = self.activator.activated()
        summary = self.activator.summary()
        new_status = bool(self.alarm_model.up) != alarm_status

        self.__log_alarm_status(alarm_status, summary, new_status)

        if not new_status:
            return

        queries.update_alarm_status(self.alarm_model.id, alarm_status, self.db)
        self.__send_alarm_to_iota(alarm_status, summary)

        actions = ActionFactory().get_alarm_actions(
            self.alarm_model.id,
            alarm_status,
            summary,
            self.db,
        )

        for action in actions:
            try:
                action.run()

            except Exception as e:
                logging.error(f"Error ejecutando la accion {action.name}: {e}")

    def __log_alarm_status(
        self, alarm_status: bool, summary: str, new_status: bool
    ) -> None:
        if new_status:
            message = "Alarma disparada" if alarm_status else "Alarma rearmada"
        else:
            message = "Alarma comprobada"

        now = datetime.now()
        create_info_log(
            self.db,
            {
                "datetime": now,
                "created_at": now,
                "updated_at": now,
                "message": message,
                "extra": {
                    "alarm_id": self.alarm_model.id,
                    "alarm_status_up": alarm_status,
                    "alarm_activation_conditions": summary,
                },
                "resource_type": ResourceType.ALARMS,
                "resource_id": self.alarm_model.id,
            },
        )

        logging.info(f"Alarma {self.alarm_model.id}: up={alarm_status} ({summary})")

    def __send_alarm_to_iota(self, alarm_status: bool, summary: str) -> None:
        """
        Publica el cambio de estado en el IoT Agent para que quede la serie
        temporal de la alarma. Es historico, no parte de la decision: si el
        servicio de la alarma no esta dado de alta, no se interrumpe nada.
        """
        if not self.iota_service_apikey or not self.iota_service_resource:
            logging.warning(
                f"Sin servicio del IoT Agent para la alarma {self.alarm_model.id}: "
                "no se guarda su historico"
            )
            return

        try:
            iota.publish_data(
                id=str(self.alarm_model.id),
                apikey=self.iota_service_apikey,
                resource=self.iota_service_resource,
                body={
                    "status": 1 if alarm_status else 0,
                    "alarm_activation_conditions": summary,
                    "TimeInstant": datetime.now().isoformat(),
                },
            )

        except Exception as e:
            logging.error(f"Error enviando el estado de la alarma al IoT Agent: {e}")
