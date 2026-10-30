from typing import List, Optional, Tuple

from models.device_entity_model import DeviceEntity
from models.device_model import Device
from models.device_types_model import DeviceType
from models.entity_model import Entity

import models.crud.crud_entity_properties as crud_entity_properties

from .snapshot_base import SnapshotPayloadBuilder


class DeviceInventoryPayloadBuilder(SnapshotPayloadBuilder):
    """
    Inventory of the linked devices, and of the devices of the linked entities:

    {"devices": [{"general": {"nombreSensor", "idSensor", "coordenadas": {"lat", "lon"},
                              "nombre", "modelo", "familia", "descripcion", "numeroSerie"},
                  "groupings": []}]}
    """

    ITEMS_KEY = "devices"

    def build_items(self) -> List[Tuple[str, dict]]:
        """
        Keyed by the device serial, or by its id when it has none.
        """
        device_ids = set(self.linked_device_ids()) | self.__devices_of_linked_entities()
        if not device_ids:
            return []

        rows = (
            self.iris_db.query(Device, DeviceType)
            .outerjoin(DeviceType, DeviceType.id == Device.device_type_id)
            .filter(Device.id.in_(device_ids))
            .order_by(Device.id)
            .all()
        )
        main_entities = self.__main_entities(device_ids)
        sensor_names = self.names_by_urn([entity.urn for entity in main_entities.values()])

        devices = []
        for device, device_type in rows:
            entity = main_entities.get(device.id)
            devices.append(
                (
                    device.serial or str(device.id),
                    {
                        "general": {
                            "nombreSensor": sensor_names.get(entity.urn, self.urn_id(entity.urn)) if entity else None,
                            "idSensor": entity.urn if entity else None,
                            "coordenadas": self.__coordinates(entity),
                            "nombre": device.name,
                            "modelo": device_type.name if device_type else None,
                            "familia": device_type.category if device_type else None,
                            "descripcion": device.description,
                            "numeroSerie": device.serial,
                        },
                        # PENDING: what a grouping is (group and value) is not defined yet.
                        "groupings": [],
                    },
                )
            )

        return devices

    def __devices_of_linked_entities(self) -> set:
        entity_ids = self.linked_entity_ids()
        if not entity_ids:
            return set()

        rows = (
            self.iris_db.query(DeviceEntity.device_id)
            .filter(DeviceEntity.entity_id.in_(entity_ids))
            .distinct()
            .all()
        )
        return {row[0] for row in rows}

    def __main_entities(self, device_ids) -> dict:
        """
        {device_id: Entity} with the main entity of each device: the one that reports.
        """
        rows = (
            self.iris_db.query(DeviceEntity.device_id, Entity)
            .join(Entity, Entity.id == DeviceEntity.entity_id)
            .filter(DeviceEntity.device_id.in_(device_ids))
            .filter(DeviceEntity.entity_type == "main")
            .all()
        )
        return {device_id: entity for device_id, entity in rows}

    def __coordinates(self, entity) -> Optional[dict]:
        if entity is None:
            return None

        try:
            location = crud_entity_properties.get_entity_location(entity.id, self.realtime_db)
        except Exception:
            location = None

        # GeoJSON keeps [lon, lat].
        coordinates = (location or {}).get("coordinates") if isinstance(location, dict) else None
        if not coordinates or len(coordinates) < 2:
            return None

        return {"lat": coordinates[1], "lon": coordinates[0]}
