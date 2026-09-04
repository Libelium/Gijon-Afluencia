from datetime import datetime
from typing import Dict

import models.crud.crud_entity as crud_entity
import models.crud.crud_entity_commands as crud_entity_commands
from config.logging import appLogging as logging
from db.session_helpers import realtime_session
from helpers.aether_link.aether_link_helper import update_on_context_broker
from jobs.alarms.action.logged_action import LoggedAction
from sqlalchemy.orm import Session

CHANNEL = "action_entity_command"


class EntityCommandAction(LoggedAction):
    """
    Accion que envia comandos a las entidades cuando la alarma cambia de estado.

    `commands` tiene la forma { "<entity_id>": { "<comando>": "<valor>" } }. El
    urn, el tenant y el scope de cada entidad se resuelven al ejecutar, y el
    comando se escribe como atributo Command en el Context Broker a traves del
    aether-link: de ahi el IoT Agent lo entrega al fiware-manager, que lo guarda
    pendiente hasta que el dispositivo vuelve a reportar.

    Tras un envio correcto se marca el comando como pendiente en la base de
    tiempo real, igual que hace el envio manual: es lo que la interfaz lee para
    mostrarlo, y quien lo baja es el trabajo de tiempo real cuando la entidad
    vuelve a reportar.
    """

    def __init__(
        self,
        name: str,
        commands: Dict[str, Dict[str, str]],
        alarm_id: int,
        db: Session,
    ):
        super().__init__(name, CHANNEL, alarm_id, db)
        self.commands = commands or {}

    def run(self) -> None:
        logging.info(f"Ejecutando accion {CHANNEL} de la alarma {self.alarm_id}")

        if not self.commands:
            self._log_warning("La accion no tiene comandos configurados")
            return

        sent = {}
        failed = {}
        entity_ids = self.__entity_ids(failed)
        entities = crud_entity.get_entity_urns_for_ids(
            list(entity_ids.values()), self.db
        )
        pending = []

        for entity_id, entity_commands in self.commands.items():
            if entity_id not in entity_ids:
                continue

            entity = entities.get(entity_ids[entity_id])

            if not entity:
                failed[str(entity_id)] = "la entidad no existe"
                continue

            urn, tenant, scope = entity

            for command, value in entity_commands.items():
                result = update_on_context_broker(
                    urn, tenant, scope, {command: {"type": "Command", "value": value}}
                )

                if result.get("updated"):
                    sent.setdefault(urn, []).append(command)
                    pending.append(
                        (urn, tenant, scope, entity_ids[entity_id], command, value)
                    )
                else:
                    failed[f"{urn}:{command}"] = str(result.get("response"))

        self.__mark_pending(pending)
        self.__log_results(sent, failed)

    def __mark_pending(self, pending: list) -> None:
        """
        El comando ya salio hacia el dispositivo: si no se puede anotar el
        pendiente, se registra y se sigue, pero no se deshace el envio.
        """
        if not pending:
            return

        try:
            with realtime_session() as realtime_db:
                now = datetime.now()

                for urn, tenant, scope, entity_id, command, value in pending:
                    crud_entity_commands.update_entity_command(
                        {
                            "urn": urn,
                            "tenant": tenant,
                            "scope": scope,
                            "entity_id": entity_id,
                            "name": command,
                            "pending": True,
                            "pending_value": None if value is None else str(value),
                            "status_timestamp": now,
                        },
                        realtime_db,
                    )

        except Exception as e:
            logging.error(
                f"Comandos de la alarma {self.alarm_id} enviados pero sin marcar "
                f"como pendientes: {e}"
            )

    def __entity_ids(self, failed: dict) -> Dict[str, int]:
        entity_ids = {}

        for entity_id in self.commands:
            try:
                entity_ids[entity_id] = int(entity_id)

            except (TypeError, ValueError):
                failed[str(entity_id)] = "identificador de entidad no valido"

        return entity_ids

    def __log_results(self, sent: dict, failed: dict) -> None:
        if sent:
            self._log_info(
                "Comandos enviados a las entidades de la alarma", {"commands": sent}
            )

        if failed:
            logging.error(f"Comandos sin enviar de la alarma {self.alarm_id}: {failed}")
            self._log_error("Comandos sin enviar", {"errors": failed})
