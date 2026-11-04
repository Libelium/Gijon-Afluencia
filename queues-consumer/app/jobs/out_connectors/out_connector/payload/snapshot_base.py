from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

import models.crud.crud_entity_properties as crud_entity_properties
import models.crud.crud_out_connectors as crud_out_connectors
from models.device_model import Device
from models.entity_model import Entity


class SnapshotPayloadBuilder(ABC):
    """
    Builds the current state of the models linked to an out connector, read from the
    realtime database: either one message with every item, or one message per item id
    (the {id} topic variable). Returns None / {} when there is nothing to send.
    """

    # Key of the list that holds the items in every message.
    ITEMS_KEY = "lecturas"

    def __init__(self, out_connector_id: int, iris_db: Session, realtime_db: Session):
        self.out_connector_id = out_connector_id
        self.iris_db = iris_db
        self.realtime_db = realtime_db

    @abstractmethod
    def build_items(self) -> List[Tuple[str, dict]]:
        """
        (id, item) pairs, in sending order. The id is the one the message itself uses
        for the item: the point of interest, the origin sensor, the device serial.
        """

    def build_payload(self) -> Optional[dict]:
        items = self.build_items()
        return {self.ITEMS_KEY: [item for _, item in items]} if items else None

    def build_payloads_by_id(self) -> Dict[str, dict]:
        """
        One message per id, each with only that id's items, keeping their order.
        """
        grouped: Dict[str, list] = {}
        for item_id, item in self.build_items():
            grouped.setdefault(item_id, []).append(item)
        return {item_id: {self.ITEMS_KEY: items} for item_id, items in grouped.items()}

    def linked_entity_ids(self) -> List[int]:
        return crud_out_connectors.get_linked_model_ids(
            self.out_connector_id, Entity.__tablename__, self.iris_db
        )

    def linked_device_ids(self) -> List[int]:
        return crud_out_connectors.get_linked_model_ids(
            self.out_connector_id, Device.__tablename__, self.iris_db
        )

    def properties_by_entity(
        self, entity_ids: List[int], names: List[str]
    ) -> Dict[int, dict]:
        """
        {entity_id: {property name: EntityProperty}} for the given properties.
        """
        result: Dict[int, dict] = {}
        if not entity_ids:
            return result

        for prop in crud_entity_properties.get_entity_properties(
            entity_ids, names, self.realtime_db
        ):
            result.setdefault(prop.entity_id, {})[prop.name] = prop

        return result

    def names_by_urn(self, urns: List[str]) -> Dict[str, str]:
        """
        Current `name` property of each entity, by URN.
        """
        if not urns:
            return {}

        return {
            prop.urn: prop.value
            for prop in crud_entity_properties.get_entity_properties_by_urn(
                list(urns), "name", self.realtime_db
            )
            if prop.value
        }

    @staticmethod
    def urn_id(urn: str) -> str:
        """
        Last segment of an NGSI-LD URN: urn:ngsi-ld:CrowdFlowZone:playa -> playa.
        """
        return urn.rsplit(":", 1)[-1] if urn else urn

    @staticmethod
    def iso_utc(value) -> Optional[str]:
        """
        ISO 8601 in UTC with a Z: from a datetime or from an ISO string.
        """
        if value is None:
            return None

        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return value

        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def number(value: Optional[str]):
        """
        The realtime database stores every value as text.
        """
        if value is None:
            return None

        try:
            number = float(value)
        except ValueError:
            return None

        return int(number) if number.is_integer() else number
