from typing import List

import jobs.alarms.queries as queries
from config.logging import appLogging as logging
from jobs.alarms.action.action import Action
from jobs.alarms.action.email_action import CHANNEL as EMAIL_CHANNEL
from jobs.alarms.action.email_action import EmailAction
from jobs.alarms.action.entity_command_action import (
    CHANNEL as ENTITY_COMMAND_CHANNEL,
)
from jobs.alarms.action.entity_command_action import EntityCommandAction
from jobs.alarms.action.http_push_action import CHANNEL as HTTP_PUSH_CHANNEL
from jobs.alarms.action.http_push_action import HttpPushAction
from jobs.alarms.action.notification_action import (
    NotificationAction,
    NotificationChannel,
)
from jobs.alarms.models import AlarmTrigger
from sqlalchemy.orm import Session


class ActionFactory:
    """
    Construye las acciones que hay que ejecutar cuando una alarma cambia de
    estado.
    """

    def get_alarm_actions(
        self,
        alarm_id: int,
        alarm_up_status: bool,
        summary: str,
        db: Session,
    ) -> List[Action]:
        """
        Acciones ligadas a la alarma para la transicion que acaba de ocurrir.
        """
        trigger = AlarmTrigger.UP if alarm_up_status else AlarmTrigger.DOWN
        action_ids = queries.get_alarm_action_ids(alarm_id, trigger, db)

        if not action_ids:
            return []

        actions: List[Action] = []
        actions += self.__notification_actions(action_ids, alarm_id, summary, db)
        actions += self.__email_actions(action_ids, alarm_id, summary, db)
        actions += self.__http_push_actions(
            action_ids, alarm_id, alarm_up_status, summary, db
        )
        actions += self.__entity_command_actions(action_ids, alarm_id, db)

        # Solo deberian quedarse fuera las acciones de canales que el backend ya
        # no permite configurar y siguen guardadas de antes.
        unsupported = len(action_ids) - len(actions)
        if unsupported > 0:
            logging.warning(
                f"La alarma {alarm_id} tiene {unsupported} accion(es) de un canal "
                "no soportado por el motor de alarmas: no se ejecutaran"
            )

        return actions

    def __notification_actions(
        self, action_ids: List[int], alarm_id: int, summary: str, db: Session
    ) -> List[Action]:
        actions: List[Action] = []

        for channel in NotificationChannel:
            for action_model, channel_model in queries.get_actions_of_type(
                action_ids, channel.value, db
            ):
                actions.append(
                    NotificationAction(
                        name=action_model.name,
                        channel=channel,
                        destination=self.__destination(channel, channel_model),
                        message=channel_model.message,
                        alarm_id=alarm_id,
                        summary=summary,
                        db=db,
                    )
                )

        return actions

    def __email_actions(
        self, action_ids: List[int], alarm_id: int, summary: str, db: Session
    ) -> List[Action]:
        return [
            EmailAction(
                name=action_model.name,
                destination=self.__destinations(channel_model.destination),
                subject=channel_model.subject,
                content=channel_model.content,
                alarm_id=alarm_id,
                summary=summary,
                db=db,
            )
            for action_model, channel_model in queries.get_actions_of_type(
                action_ids, EMAIL_CHANNEL, db
            )
        ]

    def __http_push_actions(
        self,
        action_ids: List[int],
        alarm_id: int,
        alarm_up_status: bool,
        summary: str,
        db: Session,
    ) -> List[Action]:
        return [
            HttpPushAction(
                name=action_model.name,
                url_template=channel_model.url_template,
                method=channel_model.method,
                authorization=channel_model.authorization,
                alarm_id=alarm_id,
                alarm_up=alarm_up_status,
                summary=summary,
                db=db,
            )
            for action_model, channel_model in queries.get_actions_of_type(
                action_ids, HTTP_PUSH_CHANNEL, db
            )
        ]

    def __entity_command_actions(
        self, action_ids: List[int], alarm_id: int, db: Session
    ) -> List[Action]:
        return [
            EntityCommandAction(
                name=action_model.name,
                commands=channel_model.commands,
                alarm_id=alarm_id,
                db=db,
            )
            for action_model, channel_model in queries.get_actions_of_type(
                action_ids, ENTITY_COMMAND_CHANNEL, db
            )
        ]

    @staticmethod
    def __destination(channel: NotificationChannel, channel_model) -> str:
        if channel == NotificationChannel.TELEGRAM:
            return str(channel_model.chat_id)

        return channel_model.phone

    @staticmethod
    def __destinations(destination: str) -> List[str]:
        """
        El backend guarda los destinatarios del correo unidos por '#'.
        """
        if not destination:
            return []

        return [address.strip() for address in destination.split("#") if address.strip()]
