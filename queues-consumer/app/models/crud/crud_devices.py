from typing import Any, Dict, List
from models.entity_model import Entity
from models.entity_properties_model import EntityProperty
from models.device_entity_model import DeviceEntity
from models.device_model import Device
from models.device_types_model import DeviceType
from config.logging import appLogging as logging
from datetime import datetime

from sqlalchemy.orm import Session


def get_device_and_type_code(entity_id: int, db: Session) -> Device | None:
    """
    Returns the device and the type code of the entity with the given id.
    """

    device = (
        db.query(Device, DeviceType.code)
        .join(DeviceType, DeviceType.id == Device.device_type_id)
        .join(DeviceEntity, DeviceEntity.device_id == Device.id)
        .filter(DeviceEntity.entity_id == entity_id)
        .first()
    )

    if not device:
        return None, None

    return device


def get_device_id_for_main_entity(entity_id: int, db: Session) -> Device | None:
    """
    Returns the device whose main entity is the one with the given id.
    """

    query_result = (
        db.query(DeviceEntity.device_id)
        .filter(DeviceEntity.entity_id == entity_id, DeviceEntity.entity_type == "main")
        .first()
    )

    if not query_result:
        return None

    return query_result[0]


def get_device_id_for_entity(entity_id: int, db: Session) -> Device | None:
    """
    Returns the device whose entity is the one with the given id.
    """

    query_result = (
        db.query(DeviceEntity.device_id)
        .filter(DeviceEntity.entity_id == entity_id)
        .first()
    )

    if not query_result:
        return None

    return query_result[0]


def get_device_by_serial(serial: str, db: Session) -> Device | None:
    """
    Returns the device with the given serial.
    """

    query_result = db.query(Device).filter(Device.serial == serial).first()

    if not query_result:
        return None

    return query_result


def get_device_serial(device_id: int, db: Session) -> str | None:
    """
    Returns the device serial
    """

    serial = db.query(Device.serial).filter(Device.id == device_id).first()

    return serial[0] if serial else None


def get_devices(device_ids: List[int], db: Session) -> List[Device]:
    """
    Returns the devices
    """

    devices = db.query(Device).filter(Device.id.in_(device_ids)).all()

    return devices


def get_device_case_id(device_id: int, db: Session) -> str | None:
    """
    Returns the device case id
    """

    case_id = db.query(Device.case_id).filter(Device.id == device_id).first()

    return case_id[0] if case_id else None


def get_entities_ids_for_device_id(device_id: int, db: Session) -> List[int]:
    """
    Returns the entities ids related to the device with the given id.
    """

    entities = (
        db.query(DeviceEntity.entity_id)
        .filter(DeviceEntity.device_id == device_id)
        .all()
    )

    return [entity[0] for entity in entities]


def update(device: Device, db: Session):
    """
    Updates the device in the database.
    """

    db.add(device)
    db.commit()
    db.refresh(device)


def get_related_entities_attrs(
    devices: List[int], attrs: List[str], main_db: Session, realtime_db: Session
) -> Dict[str, Any]:
    """
    Returns a dictionary with the attributes and its values like:
    {
        "entity_id": {
            "urn": urn,
            "tenant": tenant,
            "scope": scope,
            "attribute_name": {
                "value": value,
                "value_type": value_type,
                "timestamp": timestamp (datetime),
                "id": database_id
            },
            ...
        },
        ...
    }

    Empty entities are included in the dictionary
    (entities without the requested attributes).
    {
        "entity_id": {},
        ...
    }
    """

    if not devices:
        return {}

    # get related entities
    related_entities = (
        main_db.query(DeviceEntity.entity_id, Entity.urn, Entity.tenant, Entity.scope)
        .filter(DeviceEntity.device_id.in_(devices))
        .join(Entity, Entity.id == DeviceEntity.entity_id)
        .all()
    )

    if not related_entities:
        return {}

    entity_attrs = {
        entity[0]: {
            "urn": entity[1],
            "tenant": entity[2],
            "scope": entity[3],
        }
        for entity in related_entities
    }

    # get attrs
    entity_raw_attrs = realtime_db.query(
        EntityProperty.id,
        EntityProperty.entity_id,
        EntityProperty.name,
        EntityProperty.value,
        EntityProperty.value_type,
        EntityProperty.timestamp,
    ).filter(
        EntityProperty.entity_id.in_(entity_attrs.keys()),
        EntityProperty.name.in_(attrs),
    )

    for (
        database_id,
        entity_id,
        attr_name,
        attr_value,
        attr_value_type,
        timestamp,
    ) in entity_raw_attrs:

        if attr_name in entity_attrs[entity_id]:
            logging.warning(
                f"Multiple attributes found for entity {entity_id}, using most recent one"
            )

            if entity_attrs[entity_id][attr_name]["timestamp"] > timestamp:
                continue

        entity_attrs[entity_id][attr_name] = {
            "id": database_id,
            "value": attr_value,
            "value_type": attr_value_type,
            "timestamp": timestamp,
        }

    return entity_attrs
