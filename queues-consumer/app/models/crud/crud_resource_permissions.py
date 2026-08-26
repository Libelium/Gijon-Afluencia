from typing import Any, List
from sqlalchemy.orm import Session
from schemas.resource_schema import ResourceType
from models.resource_permission_model import (
    ModelHasResourcePermission,
    ResourcePermission,
    ResourcePermissionType,
)
from models.user_model import User
import models.crud.crud_organizations as crud_organizations
from config.logging import appLogging as logging


def assign_default_permissions_to_user(
    user_id: int,
    resource: Any,
    db: Session,
    assign_to_admin=True,
    assign_to_organization=True,
) -> List[ModelHasResourcePermission]:
    """
    Assign the default permissions to the user for the given resource.
    The default permissions are READ and UPDATE.
    """

    permission_query_result = (
        db.query(ResourcePermission.id)
        .where(
            ResourcePermission.name.in_(ResourcePermissionType.default_permissions())
        )
        .all()
    )

    permission_ids = [permission_id for permission_id, in permission_query_result]

    logging.info(
        f"Assigning default permissions to user {user_id} for resource {resource.__tablename__}"
    )

    logging.info(f"Permission ids: {permission_ids}")

    organization = None
    organization_admin = None

    if assign_to_admin or assign_to_organization:

        organization = crud_organizations.get_user_organization(user_id, db)

        if not organization:
            raise Exception(
                f"User with id {user_id} is not an admin of any organization"
            )

        organization_admin = organization.admin

    user_permissions = [
        ModelHasResourcePermission(
            model_id=user_id,
            model_type=ResourceType.USERS.value,
            resource_permission_id=permission_id,
            resource_type=resource.__tablename__,
            resource_id=resource.id,
        )
        for permission_id in permission_ids
    ]

    admin_permissions = [
        ModelHasResourcePermission(
            model_id=organization_admin,
            model_type=ResourceType.USERS.value,
            resource_permission_id=permission_id,
            resource_type=resource.__tablename__,
            resource_id=resource.id,
        )
        for permission_id in permission_ids
        if assign_to_admin and organization_admin != user_id
    ]

    db.bulk_save_objects(user_permissions + admin_permissions)

    if assign_to_organization:
        crud_organizations.assign_resource_to_organization(
            organization.id, resource, db
        )

    db.commit()

    return user_permissions

def get_models_resource_relation(
    db: Session,
    ids: List[int]
) -> List[ModelHasResourcePermission]:
    """
    Returns all ModelHasResourcePermission rows whose resource_id is in the given list of ids
    and resource_type == 'devices'.
    """
    return (
        db.query(ModelHasResourcePermission)
          .filter(
              ModelHasResourcePermission.resource_id.in_(ids),
              ModelHasResourcePermission.resource_type == ResourceType.DEVICES.value,
              ModelHasResourcePermission.model_type == ResourceType.WORKSPACES.value,
          )
          .all()
    )
    


def bulk_create_model_has_resource_permissions(
    db: Session,
    model_has_resource: List[ModelHasResourcePermission]
) -> List[ModelHasResourcePermission]:
    """
    Inserts multiple ModelHasResourcePermission instances in bulk.

    permissions: list of pre-built ModelHasResourcePermission instances.

    Returns the same instances with their IDs assigned after commit.
    """
    # Añade todas las instancias al Session de forma clásica
    db.add_all(model_has_resource)
    db.commit()

    return model_has_resource
