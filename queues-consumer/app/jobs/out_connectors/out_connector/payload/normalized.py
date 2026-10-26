from .base_payload import BasePayloadBuilder
from schemas.entity_data_notification import EntityDataNotification
from schemas.payload_schema import NormalizedPayload
from models.crud.crud_devices import get_device_serial, get_device_case_id

from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict


class NormalizedPayloadBuilder(BasePayloadBuilder):
    """
    This class is responsible for building the normalized payload for the out_connectors.
    """

    def __init__(self, iris_db: Session, use_readable_names: bool = False):
        self.iris_db = iris_db
        self.use_readable_names = use_readable_names

    def build_payload(
        self, entity_data: EntityDataNotification
    ) -> NormalizedPayload:
        attr_names = [attr.name for attr in entity_data.data]
        names_map = self.get_attr_names_map(attr_names, self.use_readable_names, self.iris_db)

        payload = {}

        for attr in entity_data.data:
            payload[names_map[attr.name]] = {
                "value": attr.value,
                "type": self.__get_attr_value_col(attr.value),
                "ts": datetime.fromtimestamp(attr.timestamp).isoformat(),
                "metadata": {"units": attr.units if attr.units else None},
            }

        payload["id"] = entity_data.urn

        device_id = entity_data.devices[0] if entity_data.devices else None
        if device_id:
            payload = self.__add_device_info(payload, device_id, entity_data)

        return payload

    def __add_device_info(
        self,
        payload: NormalizedPayload,
        device_id: str,
        entity_data: EntityDataNotification,
    ) -> NormalizedPayload:
        payload["serial"] = get_device_serial(device_id, self.iris_db)
        payload["case_id"] = get_device_case_id(device_id, self.iris_db)
        payload = self.__add_aux_serial(payload, entity_data)

        return payload

    def __add_aux_serial(
        self, payload: NormalizedPayload, entity_data: EntityDataNotification
    ) -> NormalizedPayload:
        if "ONS" in entity_data.urn:
            payload["aux_serial"] = entity_data.urn.split(":")[-1]

        return payload

    def __get_attr_value_col(self, attr) -> str:
        """
        Get the correct attribute value column, based on the attribute type.
        It returns a dict to be directly unpacked in the EntityData constructor.
        """

        # Define a mapping from Python types to column names and value types
        type_to_column: Dict[type, str] = {
            None: "none",
            bool: "boolean",
            int: "float",
            float: "float",
            list: "array",
            dict: "json",
            str: "string",
        }

        value_data_type = type(attr) if attr is not None else None

        value_type = type_to_column.get(value_data_type, "json")

        return value_type
