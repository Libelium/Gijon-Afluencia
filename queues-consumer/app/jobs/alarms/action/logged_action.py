from datetime import datetime

from jobs.alarms.action.action import Action
from models.crud.crud_log import (
    create_error_log,
    create_info_log,
    create_warning_log,
)
from schemas.resource_schema import ResourceType
from sqlalchemy.orm import Session


def with_summary(message: str, summary: str) -> str:
    """
    Texto del aviso: lo que configuro quien creo la alarma y, detras, el resumen
    de las condiciones que la han hecho saltar.
    """
    if not summary:
        return message

    return f"{message}\n\n{summary}"


class LoggedAction(Action):
    """
    Base de las acciones de alarma: todas dejan en el log de la plataforma como
    ha ido su ejecucion, con la alarma como recurso.
    """

    def __init__(self, name: str, channel: str, alarm_id: int, db: Session):
        self.name = name
        self.channel = channel
        self.alarm_id = alarm_id
        self.db = db

    def _log_info(self, message: str, extra: dict = None) -> None:
        self.__log(create_info_log, message, extra)

    def _log_warning(self, message: str, extra: dict = None) -> None:
        self.__log(create_warning_log, message, extra)

    def _log_error(self, message: str, extra: dict = None) -> None:
        self.__log(create_error_log, message, extra)

    def __log(self, create_log, message: str, extra: dict) -> None:
        now = datetime.now()
        create_log(
            self.db,
            {
                "datetime": now,
                "created_at": now,
                "updated_at": now,
                "message": message,
                "extra": {
                    "action_name": self.name,
                    "channel": self.channel,
                    "alarm_id": self.alarm_id,
                    **(extra or {}),
                },
                "resource_type": ResourceType.ALARMS,
                "resource_id": self.alarm_id,
            },
        )
