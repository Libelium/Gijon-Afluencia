from enum import Enum

from config.logging import appLogging as logging
from jobs.alarms.action import senders
from jobs.alarms.action.logged_action import LoggedAction, with_summary
from sqlalchemy.orm import Session


class NotificationChannel(str, Enum):
    """
    Canales de mensaje corto soportados, con el actionable_type que les
    corresponde en la tabla actions.
    """

    TELEGRAM = "action_telegram"
    SMS = "action_sms"
    WHATSAPP = "action_whatsapp"

    def send(self, destination: str, message: str) -> None:
        SENDERS[self](destination, message)


SENDERS = {
    NotificationChannel.TELEGRAM: senders.send_telegram,
    NotificationChannel.SMS: senders.send_sms,
    NotificationChannel.WHATSAPP: senders.send_whatsapp,
}


class NotificationAction(LoggedAction):
    """
    Accion que avisa a una persona por uno de los canales de mensaje corto. El
    texto es el que configuro quien creo la alarma; el resumen de las
    condiciones se añade detras para que el aviso diga por que ha saltado.
    """

    def __init__(
        self,
        name: str,
        channel: NotificationChannel,
        destination: str,
        message: str,
        alarm_id: int,
        summary: str,
        db: Session,
    ):
        super().__init__(name, channel.value, alarm_id, db)
        self.notification_channel = channel
        self.destination = destination
        self.message = message
        self.summary = summary

    def run(self) -> None:
        logging.info(
            f"Ejecutando accion {self.channel} de la alarma {self.alarm_id}"
        )

        try:
            self.notification_channel.send(
                self.destination, with_summary(self.message, self.summary)
            )

        except Exception as e:
            self._log_error(
                f"Fallo el envio de la notificacion {self.channel}",
                {"error": str(e)},
            )
            return

        self._log_info(f"Notificacion {self.channel} enviada")
