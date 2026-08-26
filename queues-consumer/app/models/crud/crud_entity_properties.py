import json
from typing import Any, List
from models.entity_properties_model import EntityProperty
from sqlalchemy.orm import Session
from config.logging import appLogging as logging
from sqlalchemy.sql import func
import ast


def update_entity_property(payload: dict, db: Session, commit: bool = True) -> bool:
    timestamp = payload.get("timestamp", None)

    if timestamp == None:
        return False

    # check if there is an entity with the same urn and measure_name
    entity = (
        db.query(EntityProperty)
        .filter(EntityProperty.entity_id == payload["entity_id"])
        .filter(EntityProperty.name == payload["name"])
        .first()
    )

    # we must be carefult because str(None) = "None", and
    # we want to store None as Null, not as a string "None"
    entity_value = payload["value"]
    entity_value = str(entity_value) if entity_value != None else None

    if entity:
        if entity.timestamp >= payload["timestamp"]:
            logging.debug(
                f"EntityProperty {payload['urn']}, {payload['name']} not updated. New timestamp: {payload['timestamp']} is older than existing timestamp: {entity.timestamp}."
            )
            return False

        # update the entity
        entity.value = entity_value
        entity.value_type = payload["value_type"]
        entity.timestamp = payload["timestamp"]
        entity.units = payload["units"]
        entity.updated_at = func.now()

    else:
        entity_values = EntityProperty(
            urn=payload["urn"],
            tenant=payload["tenant"],
            scope=payload["scope"],
            entity_id=payload["entity_id"],
            name=payload["name"],
            value=entity_value,
            value_type=payload["value_type"],
            timestamp=payload["timestamp"],
            units=payload["units"],
            created_at=func.now(),
            updated_at=func.now(),
        )

        db.add(entity_values)

    if commit:
        db.commit()
    return True

def get_max_property_timestamp(entity_ids: List[int], name: str, db: Session):
    return (
        db.query(func.max(EntityProperty.timestamp))
        .filter(EntityProperty.entity_id.in_(entity_ids))
        .filter(EntityProperty.name == name)
        .scalar()
    )


def get_max_property_timestamp_multi_name(entity_id: int, names: List[str], db: Session):
    """
    Returns the max timestamp across all the given attribute names for a single entity.
    """
    return (
        db.query(func.max(EntityProperty.timestamp))
        .filter(EntityProperty.entity_id == entity_id)
        .filter(EntityProperty.name.in_(names))
        .scalar()
    )


def count_entity_property_value(entity_ids: List[int], name: str, value: str, db: Session) -> int:
    return (
        db.query(func.count())
        .filter(EntityProperty.entity_id.in_(entity_ids))
        .filter(EntityProperty.name == name)
        .filter(EntityProperty.value == value)
        .scalar()
    ) or 0


def get_entity_property_bulk(entity_ids: List[int], name: str, db: Session) -> List[EntityProperty]:
    return (
        db.query(EntityProperty)
        .filter(EntityProperty.entity_id.in_(entity_ids))
        .filter(EntityProperty.name == name)
        .all()
    )

def get_entity_property(entity_id: int, name: str, db: Session) -> EntityProperty:
    return (
        db.query(EntityProperty)
        .filter(EntityProperty.entity_id == entity_id)
        .filter(EntityProperty.name == name)
        .first()
    )
    
def get_entity_property_uts_bulk(
    uts: List[tuple[str, str, str]],
    name: str,
    db: Session
) -> List[EntityProperty]:
    """
    Returns a list of EntityProperty objects for the given urn, tenant, and scope.
    """
    return (
        db.query(EntityProperty)
        .filter(
            (EntityProperty.urn, EntityProperty.tenant, EntityProperty.scope).in_(uts)
        )
        .filter(EntityProperty.name == name)
        .all()
    )


def get_entity_property_uts(
    urn: str, tenant: str, scope: str, name: str, db: Session
) -> EntityProperty:
    return (
        db.query(EntityProperty)
        .filter(EntityProperty.urn == urn)
        .filter(EntityProperty.tenant == tenant)
        .filter(EntityProperty.scope == scope)
        .filter(EntityProperty.name == name)
        .first()
    )


def get_recent_entity_property_ilike_urn(urn: str, db: Session) -> EntityProperty:
    return (
        db.query(EntityProperty)
        .filter(EntityProperty.urn.ilike(f"%{urn}%"))
        .order_by(EntityProperty.timestamp.desc())
        .first()
    )


def get_entity_location(
    entity_id: int, db: Session, location_name: str = "location"
) -> dict:
    """
    Returns the geolocation of the entity with the given id.
    """
    query_result = (
        db.query(
            EntityProperty.entity_id,
            EntityProperty.urn,
            EntityProperty.tenant,
            EntityProperty.scope,
            EntityProperty.value,
        )
        .filter(EntityProperty.entity_id == entity_id)
        .filter(EntityProperty.name == location_name)
        .first()
    )

    if not query_result:
        logging.info(f"Entity location not found for entity_id: {entity_id}")
        return None

    return json.loads(query_result.value.replace("'", '"'))


def get_entity_location_by_urn(urn: str, tenant: str, scope: str, db: Session):
    row = (
        db.query(EntityProperty)
          .filter(EntityProperty.urn == urn)
          .filter(EntityProperty.tenant == tenant)
          .filter(EntityProperty.scope == scope)
          .filter(EntityProperty.name == "location")
          .order_by(EntityProperty.timestamp.desc())
          .first()
    )

    if not row:
        return None

    try:
        return ast.literal_eval(row.value)
    except Exception as e:
        logging.error(f"Error parsing location value: {e}")
        return None