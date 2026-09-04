from typing import List, Union

from config.logging import appLogging as logging
from jobs.alarms.action import senders
from jobs.alarms.action.logged_action import LoggedAction
from sqlalchemy.orm import Session

CHANNEL = "action_http_push"


class HttpPushAction(LoggedAction):
    """
    Accion que avisa a un servicio externo con una peticion HTTP. La URL la
    escribe quien configura la alarma, asi que el destino se valida contra la
    lista blanca del entorno antes de llamarlo (ver senders.send_http_push).
    """

    def __init__(
        self,
        name: str,
        url_template: Union[str, List[dict]],
        method: str,
        authorization: str,
        alarm_id: int,
        alarm_up: bool,
        summary: str,
        db: Session,
    ):
        super().__init__(name, CHANNEL, alarm_id, db)
        # La URL se compone al ejecutar: un url_template inservible no debe
        # tumbar la construccion de las demas acciones de la alarma.
        self.url_template = url_template
        self.url = ""
        self.method = (method or "POST").upper()
        self.authorization = authorization
        self.alarm_up = alarm_up
        self.summary = summary

    def run(self) -> None:
        logging.info(f"Ejecutando accion {CHANNEL} de la alarma {self.alarm_id}")

        self.url = self.__build_url(self.url_template)

        payload = {
            "alarm_id": self.alarm_id,
            "alarm_status_up": self.alarm_up,
            "alarm_activation_conditions": self.summary,
        }

        try:
            senders.send_http_push(
                self.url, self.method, self.authorization, payload
            )

        except senders.ChannelNotConfigured as e:
            logging.warning(f"Aviso HTTP de la alarma {self.alarm_id} sin enviar: {e}")
            self._log_warning(
                "Canal de aviso HTTP no configurado: el aviso no se ha enviado",
                {"error": str(e), "url": self.url},
            )
            return

        except senders.DestinationNotAllowed as e:
            logging.warning(f"Aviso HTTP de la alarma {self.alarm_id} rechazado: {e}")
            self._log_error(
                "Destino del aviso HTTP no permitido",
                {"error": str(e), "url": self.url},
            )
            return

        except Exception as e:
            self._log_error(
                "Fallo el envio del aviso HTTP",
                {"error": str(e), "url": self.url, "method": self.method},
            )
            return

        self._log_info(
            "Aviso HTTP enviado", {"url": self.url, "method": self.method}
        )

    def __build_url(self, url_template: Union[str, List[dict]]) -> str:
        """
        url_template es jsonb: o bien la URL literal, o bien los tramos que
        escribe el backend, cada uno con su `type` y su `value`. Los tramos de
        tipo `variable` se sustituyen por el dato de la alarma que nombran; un
        nombre desconocido no aporta nada a la URL. Cualquier otra forma da una
        URL vacia, que la comprobacion de destino ya rechaza.
        """
        if isinstance(url_template, str):
            return url_template

        if not isinstance(url_template, list):
            return ""

        variables = {"alarm_id": str(self.alarm_id)}
        url = ""

        for segment in url_template:
            if not isinstance(segment, dict):
                continue

            value = segment.get("value")

            if value is None:
                continue

            if segment.get("type") == "variable":
                url += variables.get(value, "")
            else:
                url += str(value)

        return url
