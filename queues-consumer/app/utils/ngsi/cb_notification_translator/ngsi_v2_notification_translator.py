from datetime import datetime
from typing import Dict

import dateutil
from schemas.entity_data_notification import (
    CommandAttrValue,
    DataNotification,
    EntityAttr,
    EntityAttrType,
    EntityDataNotification,
)
from schemas.context_broker_notification_schema import ContextBrokerNotification
from utils.ngsi.cb_notification_translator.cb_notification_translator import (
    CBNotificationTranslator,
)


class NgsiV2NormalizedNotificationTranslator(CBNotificationTranslator):
    """
    This class is responsible for translating NGSI-V2 normalized
    notifications into Platform data notifications.
    """

    def __init__(self):
        pass

    def translate(
        self, notification: ContextBrokerNotification
    ) -> DataNotification:
        """
        This method translates NGSI-V2 normalized notifications
        into Platform data notifications.
        """
        tenant = notification.headers.get("fiware-service", None)
        scope = notification.headers.get("fiware-servicepath", None)
        notified_at = datetime.now()
        entities = notification.body.get("data", [])
        translated_entities = [
            self.translate_entity(entity, notified_at, tenant, scope)
            for entity in entities
        ]

        return DataNotification(
            notified_at=notified_at.timestamp(), data=translated_entities
        )

    def translate_entity(
        self, entity: dict, default_timestamp: datetime, tenant: str, scope: str
    ) -> EntityDataNotification:
        """
        This method translates a single NGSI-LD normalized entity
        into a Platform data notification.
        WARNING: It does not fill the db_id.
        """
        urn = entity.get("id", None)
        if urn is None:
            raise ValueError("The entity id is missing")

        entity_type = entity.get("type", None)
        if entity_type is None:
            raise ValueError("The entity type is missing")

        data = []
        cmds = {}
        ignore_attrs = ["id", "type", "TimeInstant"]
        for attr_name, attr_value in entity.items():

            if attr_name in ignore_attrs:
                continue

            entity_attr = self.__translate_normalized_attribute(
                attr_name, attr_value, default_timestamp
            )

            if entity_attr.type == EntityAttrType.COMMAND:
                old_cmd = cmds.get(entity_attr.name, None)
                if old_cmd is None:
                    cmds[entity_attr.name] = entity_attr
                    continue
                entity_attr = self.__merge_cmd_info_status(old_cmd, entity_attr)
                entity_attr.value = entity_attr.value.dict()

            data.append(entity_attr)

        return EntityDataNotification(
            urn=urn,
            tenant=tenant,
            scope=scope,
            type=entity_type,
            data=data,
            notified_at=default_timestamp.timestamp(),
        )

    def __is_command_info(self, attr: dict) -> bool:
        """
        This method checks if an attribute is a command info.
        """
        return attr.get("type", None) == "commandResult"

    def __is_command_status(self, attr: dict) -> bool:
        """
        This method checks if an attribute is a command status.
        """
        return attr.get("type", None) == "commandStatus"

    def __get_cmd_name(self, attr_name: str) -> str:
        """
        This method gets the command name from the attribute key.
        """
        return attr_name.split("_")[0]

    def __merge_cmd_info_status(
        self, cmd_info: EntityAttr, cmd_status: EntityAttr
    ) -> EntityAttr:
        """
        This method merges the command info and status into a single
        Platform attribute.
        """

        if cmd_info.name != cmd_status.name:
            raise ValueError("The command info and status must have the same name")

        return EntityAttr(
            name=cmd_info.name,
            value=CommandAttrValue(
                info=cmd_info.value.info,
                status=cmd_status.value.status,
                info_timestamp=cmd_info.timestamp,
                status_timestamp=cmd_status.timestamp,
            ),
            type=EntityAttrType.COMMAND,
            units=cmd_info.units,
            timestamp=max(cmd_info.timestamp, cmd_status.timestamp),
        )

    def __translate_normalized_attribute(
        self, attr_name: str, attr_value: dict, default_timestamp: datetime
    ) -> EntityAttr:
        """
        This method translates a normalized attribute
        into a Platform attribute.
        """
        metadata: Dict = attr_value.get("metadata", {})

        # Get the timestamp from the metadata or use the default timestamp
        timeInstant = metadata.get("TimeInstant", {}).get("value", None)
        timestamp_override = False if timeInstant else True
        timestamp = (
            dateutil.parser.parse(timeInstant).timestamp()
            if timeInstant is not None
            else default_timestamp.timestamp()
        )

        # Get the units
        units = metadata.get("UnitCode", {}).get("value", None)

        value = attr_value.get("value", None)

        ngsi_v2_type = attr_value.get("type", None)

        # Translate the NGSI-V2 type into a Platform type
        is_info = self.__is_command_info(attr_value)
        is_status = self.__is_command_status(attr_value)
        if is_info or is_status:
            attr_type = EntityAttrType.COMMAND
            attr_name = self.__get_cmd_name(attr_name)
            value = CommandAttrValue(
                info=value if is_info else None,
                status=value if is_status else None,
                info_timestamp=timestamp if is_info else 0,
                status_timestamp=timestamp if is_status else 0,
            )

        elif ngsi_v2_type == "Relationship":
            attr_type = EntityAttrType.RELATIONSHIP

        else:
            attr_type = EntityAttrType.PROPERTY

        return EntityAttr(
            name=attr_name,
            value=value,
            type=attr_type,
            units=units,
            timestamp=timestamp,
            timestamp_override=timestamp_override,
        )
