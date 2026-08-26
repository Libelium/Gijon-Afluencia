from typing import List
from schemas.entity_data_notification import (
    DataNotification,
    EntityAttr,
    EntityAttrType,
    EntityDataNotification,
)
from utils.ngsi.cb_notification_translator.cb_notification_translator import (
    CBNotificationTranslator,
)
from datetime import datetime
from config.logging import appLogging as logging
import utils.ngsi.ngsi_ld_utils as ngsi_ld_utils
import dateutil.parser
from schemas.context_broker_notification_schema import ContextBrokerNotification


class NgsiLdNormalizedNotificationTranslator(CBNotificationTranslator):
    """
    This class is responsible for translating NGSI-LD normalized
    notifications into Platform data notifications.
    """

    def __init__(self):
        pass

    def translate(
        self, notification: ContextBrokerNotification
    ) -> DataNotification:
        """
        This method translates NGSI-LD normalized notifications
        into Platform data notifications.
        """
        notification_body = notification.body
        if notification_body is None:
            logging.error("Notification body is None")
            raise ValueError("Notification body is None")

        headers = notification.headers
        if headers is None:
            logging.error("Notification headers are None")
            raise ValueError("Notification headers are None")

        default_timestamp = notification_body.get("notifiedAt", None)
        if default_timestamp is None:
            default_timestamp = datetime.now()
        else:
            default_timestamp = dateutil.parser.parse(default_timestamp)

        tenant = headers.get("ngsild-tenant", None)
        if tenant is None:
            logging.error("Tenant is None")
            raise ValueError("Tenant is None")

        scope = headers.get("fiware-servicepath", "/")

        return DataNotification(
            notified_at=default_timestamp.timestamp(),
            data=self.__translate_entities(
                notification_body.get("data", []), default_timestamp, tenant, scope
            ),
        )

    def __translate_entities(
        self,
        normalized_entities: List[dict],
        default_timestamp: datetime,
        tenant: str,
        scope: str,
    ) -> List[EntityDataNotification]:
        """
        This method translates a list of NGSI-LD normalized entities
        into a list of Platform entity data notifications.
        WARNING: It does not fill the db_id.
        """

        translated_data = []
        for normalized_entity in normalized_entities:
            translated_entity = self.translate_entity(
                normalized_entity, default_timestamp, tenant, scope
            )
            if translated_entity is not None:
                translated_data.append(translated_entity)
        return translated_data

    def translate_entity(
        self,
        normalized_entity: dict,
        default_timestamp: datetime,
        tenant: str,
        scope: str,
    ) -> EntityDataNotification | None:
        """
        This method translates a single NGSI-LD normalized entity
        into a Platform data notification.
        WARNING: It does not fill the db_id.
        """

        def remove_units_key(attr: dict) -> dict:
            """
            This method removes the units key from the attribute
            dictionary.
            """
            if "units" in attr:
                del attr["units"]
            return attr

        urn = normalized_entity.get("id")
        if urn is None:
            logging.error(f"Entity without id will be ignored: {normalized_entity}")
            return None

        entity_type = normalized_entity.get("type", None)
        if entity_type is None:
            return None

        entity_attrs = []

        # commands are treated differently, because they information
        # is in command_info and command_status attributes,
        # so first we need to store them in a dict and then build the
        # command itself
        command_cache = {}
        for key, value in normalized_entity.items():

            if ngsi_ld_utils.is_system_attribute(key):
                continue

            attr = self.__translate_entity_attribute(
                key, value, command_cache, default_timestamp
            )
            if attr is not None:
                entity_attrs.append(attr)

        # append commands to new elements
        for command_name, command_data in command_cache.items():
            units = command_data.get("units", None)
            entity_attrs.append(
                EntityAttr(
                    name=command_name,
                    value=remove_units_key(command_data),
                    type=EntityAttrType.COMMAND,
                    units=units,
                    timestamp=max(
                        command_data.get("info_timestamp", 0),
                        command_data.get("status_timestamp", 0),
                    ),
                )
            )

        return EntityDataNotification(
            urn=urn,
            tenant=tenant,
            scope=scope,
            type=entity_type,
            data=entity_attrs,
            notified_at=default_timestamp.timestamp(),
        )

    def __translate_entity_attribute(
        self,
        attr_name: str,
        attr_value: dict,
        command_cache: dict,
        default_timestamp: datetime,
    ) -> EntityAttr | None:
        """
        It translates a single NGSI-LD normalized entity attribute into
        a Platform entity attribute.

        If it is a command attribute (info or status), it will be stored in
        the command_cache for later processing.
        """
        if not ngsi_ld_utils.has_value(attr_value, attr_value["type"]):
            return None

        attr_type = attr_value["type"]

        observedAt = attr_value.get("observedAt", None)
        timestamp_override = False if observedAt else True
        timestamp = (
            dateutil.parser.parse(observedAt).timestamp()
            if observedAt
            else default_timestamp.timestamp()
        )

        # get the attribute value and type
        measure_value, attr_transformed_type = ngsi_ld_utils.get_attr_value_and_type(
            attr_value, attr_type
        )

        # measure_value could be none because is a null stored in
        # the context broker, therefore, it is the attr state and we
        # need to store it anyway

        units = attr_value.get("unitCode", None)

        # check if the attribute is a command info or status
        attr_is_command_info = ngsi_ld_utils.is_command_info(
            attr_name, measure_value, attr_type
        )
        attr_is_commnad_status = ngsi_ld_utils.is_command_status(
            attr_name, measure_value, attr_type
        )

        if attr_is_command_info or attr_is_commnad_status:
            # update the new_commands dict
            command_name = ngsi_ld_utils.get_command_name(attr_name)
            attr_key = "info" if attr_is_command_info else "status"
            if command_name not in command_cache.keys():
                command_cache[command_name] = {}
            command_cache[command_name][attr_key] = measure_value["@value"]
            command_cache[command_name]["units"] = units
            command_cache[command_name][f"{attr_key}_timestamp"] = timestamp
            return None

        return EntityAttr(
            name=attr_name,
            value=measure_value,
            type=attr_transformed_type,
            units=units,
            timestamp=timestamp,
            timestamp_override=timestamp_override,
        )
