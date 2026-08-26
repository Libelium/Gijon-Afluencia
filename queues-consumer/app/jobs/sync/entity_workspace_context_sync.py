from typing import List
from datetime import datetime
from sqlalchemy.orm import Session
from config.logging import appLogging as logging
from schemas.entity_data_notification import EntityDataNotification
from models.resource_permission_model import ModelHasResourcePermission
from models.crud.crud_resource_permissions import (
    get_models_resource_relation, bulk_create_model_has_resource_permissions
    )

def sync_entity_workspace_context(
    entity_data_notification: EntityDataNotification,
    db: Session
) -> None:
    """
    Ensures that if an entity was recently created and is associated with a device,
    and that device is linked to a workspace, the entity is added to the workspace's list of entities.
    It also checks whether the workspace has 'read' or 'update' permissions on the device and applies
    the same permission level to the newly linked entity.
    """
    logging.info("SYNC ENTITY WORKSPACE CONTEXT")
    device_ids: List[int] = entity_data_notification.devices
    if not device_ids:
        logging.debug("No device IDs in notification; nothing to sync.")
        return
    model_has_resources: List[ModelHasResourcePermission] = get_models_resource_relation(
        db,
        device_ids
    )
    now = datetime.now()
    new_entries = [
        ModelHasResourcePermission(
            model_id=perm.model_id,
            model_type=perm.model_type,
            resource_permission_id=perm.resource_permission_id,
            resource_type='entities',
            resource_id=entity_data_notification.db_id,
            created_at=now,
            updated_at=now,
        )
        for perm in model_has_resources
    ]

    if new_entries:
        bulk_create_model_has_resource_permissions(db, new_entries)
        
    
    entry_msgs = [
        f"entity_id={e.resource_id} → workspace={e.model_id} (perm={e.resource_permission_id})"
        for e in new_entries
    ]

    full_msg = (
        "Added to model_has_resource_permission:\n  "
        + "\n  ".join(entry_msgs)
    )

    logging.info(full_msg)