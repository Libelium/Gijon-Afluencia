from typing import List

from config.logging import appLogging as logging
from jobs.alarms.action import senders
from jobs.alarms.action.logged_action import LoggedAction, with_summary
from sqlalchemy.orm import Session

CHANNEL = "action_email"


class EmailAction(LoggedAction):
    """
    Accion que avisa por correo. El asunto y el cuerpo son los que configuro
    quien creo la alarma; detras del cuerpo va el resumen de las condiciones.
    """

    def __init__(
        self,
        name: str,
        destination: List[str],
        subject: str,
        content: str,
        alarm_id: int,
        summary: str,
        db: Session,
    ):
        super().__init__(name, CHANNEL, alarm_id, db)
        self.destination = destination
        self.subject = subject
        self.content = content
        self.summary = summary

    def run(self) -> None:
        logging.info(f"Ejecutando accion {CHANNEL} de la alarma {self.alarm_id}")

        try:
            senders.send_email(
                self.destination,
                self.subject,
                with_summary(self.content, self.summary),
            )

        except senders.ChannelNotConfigured as e:
            logging.warning(f"Correo de la alarma {self.alarm_id} sin enviar: {e}")
            self._log_warning(
                "Canal de correo no configurado: el aviso no se ha enviado",
                {"error": str(e)},
            )
            return

        except Exception as e:
            self._log_error("Fallo el envio del correo", {"error": str(e)})
            return

        self._log_info(
            "Correo enviado", {"destination": ", ".join(self.destination)}
        )
