from .base_payload import BasePayloadBuilder
import models.crud.crud_devices as crud_devices
from schemas.entity_data_notification import EntityDataNotification
from schemas.payload_schema import LegacyPayload
from models.out_connector_mqtt_model import MqttConnector as MqttConnectorModel
from models.crud.crud_out_connectors import get_units_bulk
from datetime import datetime
from sqlalchemy.orm import Session


class LegacyPayloadBuilder(BasePayloadBuilder):
    """
    This class is responsible for building the legacy payload for the out_connectors:
    one message per attribute, shaped by the connector payload_config.
    """

    def __init__(
        self,
        connector: MqttConnectorModel,
        iris_db: Session,
        use_readable_names: bool = False,
    ):
        self.connector = connector
        self.iris_db = iris_db
        self.use_readable_names = use_readable_names

    def build_payload(
        self, entity_data: EntityDataNotification
    ) -> list[LegacyPayload]:
        """
        Translate each attribute to the payload format
        configured in the connector
        """
        attr_names = [attr.name for attr in entity_data.data]
        names_map = self.get_attr_names_map(attr_names, self.use_readable_names, self.iris_db)

        attributes_for_units = [(attr.name, attr.units) for attr in entity_data.data]
        units_map = get_units_bulk(self.iris_db, attributes_for_units)

        device_id = entity_data.devices[0] if entity_data.devices else None
        device_serial = (
            crud_devices.get_device_serial(device_id, self.iris_db) if device_id else None
        )
        case_id = (
            crud_devices.get_device_case_id(device_id, self.iris_db) if device_id else None
        )

        payload = []
        for attr in entity_data.data:
            translation_map = {
                "timestamp": datetime.fromtimestamp(attr.timestamp).isoformat(),
                "value": attr.value,
                "urn": entity_data.urn,
                "tenant": entity_data.tenant,
                "scope": entity_data.scope,
                "measure": names_map[attr.name],
                "unit": units_map.get(attr.name),
            }

            # payload_config renames and filters the fields: [{key, value, active}, ...]
            message = translation_map
            if self.connector.payload_config:
                message = {
                    attr_config["value"]: translation_map[attr_config["key"]]
                    for attr_config in self.connector.payload_config
                    if attr_config["active"]
                }

            if device_serial:
                message["serial"] = device_serial

            if case_id:
                message["case_id"] = case_id

            payload.append(message)

        return payload
