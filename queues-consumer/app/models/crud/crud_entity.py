from typing import Dict, List
from models.entity_model import Entity
from models.device_model import Device
from models.device_entity_model import DeviceEntity
from models.fiware_tenant_model import FiwareTenant
from models.fiware_scope_model import FiwareScope
import models.crud.crud_tenant_scope as crud_tenant_scope
import models.crud.crud_user as crud_user
import models.resource_permission_model as resource_permission_model
from datetime import datetime, timedelta
from config.logging import appLogging as logging
from sqlalchemy.sql import func
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_


def create_entity(payload: dict, db: Session) -> Entity:
    """
    It creates the entity with the given payload.
    If the tenant or scope do not exist, they are created as well.
    """

    fiware_scope = (
        db.query(FiwareScope)
        .join(FiwareTenant, FiwareTenant.id == FiwareScope.fiware_tenant_id)
        .filter(FiwareTenant.name == payload.get("tenant"))
        .filter(FiwareScope.name == payload.get("scope"))
        .first()
    )

    if not fiware_scope:
        fiware_scope = crud_tenant_scope.create_scope(
            payload.get("scope"), payload.get("tenant"), db
        )

    entity = Entity(
        urn=payload["urn"],
        datamodel=payload["datamodel"],
        tenant=payload["tenant"],
        scope=payload["scope"],
        fiware_scope_id=fiware_scope.id,
        created_at=func.now(),
        updated_at=func.now(),
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


def get_entity_urns_for_ids(ids: List[int], db: Session) -> dict:
    """
    Returns the urns of the entities with the given ids.
    """
    query_result = (
        db.query(Entity.id, Entity.urn, Entity.tenant, Entity.scope)
        .filter(Entity.id.in_(ids))
        .all()
    )

    urns_dict = {
        result[0]: (
            result[1],
            result[2],
            result[3],
        )
        for result in query_result
    }

    return urns_dict


def get_or_create_entity(
    payload: dict, db: Session, creation_check=False
) -> tuple[Entity, bool] | Entity | None:
    urn = payload.get("urn")
    if not urn:
        return None

    tenant = payload.get("tenant")
    if not tenant:
        return None

    scope = payload.get("scope")
    if not scope:
        return None

    entity = (
        db.query(Entity)
        .filter(Entity.urn == urn, Entity.tenant == tenant, Entity.scope == scope)
        .first()
    )

    created = False

    if not entity:
        entity = create_entity(payload, db)
        created = True

    if creation_check:
        return entity, created
    else:
        return entity


def try_create(payload: dict, db: Session) -> Entity | None:
    """
    Tries to create an entity with the given payload.
    If the entity already exists, returns None.
    """
    urn = payload.get("urn")
    if not urn:
        return None

    tenant = payload.get("tenant")
    if not tenant:
        return None

    scope = payload.get("scope")
    if not scope:
        return None

    entity = (
        db.query(Entity)
        .filter(Entity.urn == urn, Entity.tenant == tenant, Entity.scope == scope)
        .first()
    )

    if entity:
        return None

    return create_entity(payload, db)


def get_related_devices(
    entity_id: int,
    db: Session,
) -> List[int]:
    """
    Returns a list of device_ids associated with the entity
    """
    related_devices = (
        db.query(Device)
        .join(DeviceEntity, Device.id == DeviceEntity.device_id)
        .filter(
            DeviceEntity.entity_id == entity_id,
        )
        .all()
    )

    return [device.id for device in related_devices]


def get_devices_with_expired_subscription(
    entity_id: int, db: Session, days_of_grace: int
) -> List[int]:
    """
    Returns a list of device_ids associated with the entity that have an expired or missing subscription.
    """
    now = datetime.now()
    grace_period = timedelta(days=days_of_grace)

    expired_devices = (
        db.query(Device)
        .join(DeviceEntity, Device.id == DeviceEntity.device_id)
        .filter(
            DeviceEntity.entity_id == entity_id,
            and_(
                Device.subscribed_until.isnot(None),
                (Device.subscribed_until + grace_period) < now,
            ),
        )
        .all()
    )
    return [device.id for device in expired_devices]


def sync_related_entities(
    related_entities: Dict[str, Entity], device_id: int, db: Session
):
    """
    Related entities is like:
    {
        entity_type (for the device_entity table, it is not the datamodel) : Entity (db model)
    }

    This method removes all relations of the device with entities not in the related_entities dict,
    and creates new relations with the entities in the related_entities dict.
    """

    # upsert related entities
    models = [
        DeviceEntity(
            device_id=device_id,
            entity_id=entity_id,
            entity_type=entity_type,
            created_at=func.now(),
            updated_at=func.now(),
        )
        for entity_type, entity_id in related_entities.items()
    ]

    db.query(DeviceEntity).filter(DeviceEntity.device_id == device_id).delete()
    db.add_all(models)
    # WARNING: do not commit before, the device cannot
    # be unrelated to the main entity at any time because
    # device ingest might depend on it
    db.commit()


def get_entities_with_permissions(datamodel: str, user_id: int, db: Session):
    # Get user entity IDs
    readable_entities = crud_user.get_user_resource_permissions(user_id, "entities", db)

    # Get user tenant IDs
    readable_tenants = crud_user.get_user_resource_permissions(
        user_id, "fiware_tenants", db
    )

    # Get user scope IDs
    readable_scopes = crud_user.get_user_resource_permissions(
        user_id, "fiware_scopes", db
    )

    # Extract model IDs
    readable_entity_ids = {entity.resource_id for entity in readable_entities}
    readable_tenant_ids = {tenant.resource_id for tenant in readable_tenants}
    readable_scope_ids = {scope.resource_id for scope in readable_scopes}

    # Query entities that belong to a tenant, a scope, or are directly assigned to the user
    # add FiwareScope.scope as tenant and FiwareTenant.name as tenant to the query to avoid N+1 queries
    entities = (
        db.query(Entity, FiwareScope.name, FiwareTenant.name)
        .join(
            FiwareScope, FiwareScope.id == Entity.fiware_scope_id
        )  # Ensure FiwareScope is joined first
        .join(FiwareTenant, FiwareTenant.id == FiwareScope.fiware_tenant_id)
        .filter(
            Entity.datamodel == datamodel,
            or_(
                Entity.id.in_(readable_entity_ids),
                Entity.fiware_scope_id.in_(readable_scope_ids),
                FiwareScope.fiware_tenant_id.in_(readable_tenant_ids),
            ),
        )
        .all()
    )

    return entities


def relate_entity_to_device(
    entity_id: int, device_id: int, entity_type: str, db: Session
):
    """
    Relates the entity with the given id to the device with the given id.
    """

    device_entity = DeviceEntity(
        device_id=device_id,
        entity_id=entity_id,
        entity_type=entity_type,
        created_at=func.now(),
        updated_at=func.now(),
    )

    db.add(device_entity)
    db.commit()
    db.refresh(device_entity)
    return device_entity


def get_entity_by_id(entity_id: int, db: Session) -> Entity | None:
    """
    Obtiene una entidad por su ID. Devuelve None si no existe.
    """
    return db.query(Entity).filter(Entity.id == entity_id).first()


def get_many_by_urn(db: Session, urns: List[str]) -> List[Entity]:
    """
    Retrieves multiple entities from the database based on a list of urns.
    Returns a list of Entity.
    """

    if not urns:
        return []
    return db.query(Entity).filter(Entity.urn.in_(urns)).all()
