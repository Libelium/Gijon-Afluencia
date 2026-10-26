from .base_payload import BasePayloadBuilder
from schemas.entity_data_notification import EntityDataNotification
from schemas.payload_schema import KeyValuePayload
from models.crud.crud_devices import get_device_serial, get_device_case_id
from sqlalchemy.orm import Session


class KeyValuePayloadBuilder(BasePayloadBuilder):
    """
    This class is responsible for building the key-value payload for the out_connect
    """

    def __init__(self, iris_db: Session, use_readable_names: bool = False):
        self.iris_db = iris_db
        self.use_readable_names = use_readable_names

    # TODO: This payload format makes no sense until the payload format is customizable
    def build_payload(self, entity_data: EntityDataNotification) -> KeyValuePayload:
        """
        Build the payload for the key-value out connector
        """
        attr_names = [attr.name for attr in entity_data.data]
        names_map = self.get_attr_names_map(attr_names, self.use_readable_names, self.iris_db)

        payload = {}
        for attr in entity_data.data:
            payload[names_map[attr.name]] = attr.value

        payload["id"] = entity_data.urn

        device_id = entity_data.devices[0] if entity_data.devices else None
        if device_id:
            payload = self.__add_device_info(payload, device_id, entity_data)

        return payload

    def __add_device_info(
        self,
        payload: KeyValuePayload,
        device_id: str,
        entity_data: EntityDataNotification,
    ) -> KeyValuePayload:
        payload["serial"] = get_device_serial(device_id, self.iris_db)
        payload["case_id"] = get_device_case_id(device_id, self.iris_db)
        payload = self.__add_aux_serial(payload, entity_data)

        return payload

    def __add_aux_serial(
        self, payload: KeyValuePayload, entity_data: EntityDataNotification
    ) -> KeyValuePayload:
        if "ONS" in entity_data.urn:
            payload["aux_serial"] = entity_data.urn.split(":")[-1]

        return payload
