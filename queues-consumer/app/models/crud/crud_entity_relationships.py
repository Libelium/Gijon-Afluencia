from models.entity_relationships_model import EntityRelationship
from sqlalchemy.orm import Session
from config.logging import appLogging as logging
from sqlalchemy.sql import func


def update_entity_relationship(payload: dict, db: Session, commit: bool = True) -> bool:
    # check if there is an entity with the same urn and measure_name and relationship value

    if payload.get("timestamp", None) == None:
        logging.warning(
            f"Timestamp not provided for EntityRelationship update. Payload: {payload}"
        )
        return False

    entity_relationship = (
        db.query(EntityRelationship)
        .filter(EntityRelationship.entity_id == payload["entity_id"])
        .filter(EntityRelationship.name == payload["name"])
        .filter(EntityRelationship.value == payload["value"])
        .first()
    )

    if entity_relationship:
        # update the entity
        if entity_relationship.timestamp >= payload["timestamp"]:
            logging.debug(
                f"EntityRelationship {payload['urn']}, {payload['name']}, {payload['value']} not updated. New timestamp is older than existing timestamp."
            )
            return False

        entity_relationship.timestamp = payload["timestamp"]
        entity_relationship.updated_at = func.now()

    else:
        entity_relationship = EntityRelationship(
            urn=payload["urn"],
            tenant=payload["tenant"],
            scope=payload["scope"],
            entity_id=payload["entity_id"],
            name=payload["name"],
            value=payload["value"],
            timestamp=payload["timestamp"],
            created_at=func.now(),
            updated_at=func.now(),
        )

        db.add(entity_relationship)

    if commit:
        db.commit()
    return True
