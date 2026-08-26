from typing import List, Optional
from models.user_model import User
from models.model_has_roles_model import ModelHasRole
from models.role_has_permissions_model import RoleHasPermission
from models.permissions_model import Permission
from models.workspace_model import Workspace
from models.workspace_has_users_model import WorkspaceHasUser
from models.resource_permission_model import ModelHasResourcePermission
from sqlalchemy.orm import Session
from db import deps
from models.organization_model import Organization


def get_user_by_id(id: int, db: Session) -> Optional[User]:
    """
    Fetches a user by ID.

    :param id: The user ID to search for.
    :param db: The database session.
    :return: The User object if found, otherwise None.
    """
    return db.query(User).filter(User.id == id).first()


def get_users_with_permission(permission: str, db: Session) -> List[User]:
    """
    Retrieves users who have a specific permission.

    :param permission: The name of the permission.
    :param db: The database session.
    :return: A list of User objects with the given permission.
    """
    permission_obj = db.query(Permission).filter(Permission.name == permission).first()
    if not permission_obj:
        return []  # Return an empty list if permission does not exist

    permission_id = permission_obj.id

    # Fetch role IDs with the given permission
    role_ids_with_permission = (
        db.query(RoleHasPermission.role_id)
        .filter(RoleHasPermission.permission_id == permission_id)
        .all()
    )

    role_ids = [role_id for (role_id,) in role_ids_with_permission]  # Unpacking tuples

    if not role_ids:
        return []

    # Fetch user IDs that have any of these roles
    user_ids = (
        db.query(ModelHasRole.model_id).filter(ModelHasRole.role_id.in_(role_ids)).all()
    )

    user_ids = [user_id for (user_id,) in user_ids]  # Unpacking tuples

    if not user_ids:
        return []

    # Fetch users with these user IDs
    return db.query(User).filter(User.id.in_(user_ids)).all()


def get_user_workspaces(user_id: int, db: Session = deps.get_db) -> List[Workspace]:
    """
    Fetches the workspaces of a user.

    :param user_id: The user ID.
    :param db: The database session.
    :return: A list of Workspace objects.
    """
    return (
        db.query(Workspace)
        .join(WorkspaceHasUser, Workspace.id == WorkspaceHasUser.workspace_id)
        .filter(WorkspaceHasUser.user_id == user_id)
        .all()
    )


def get_user_resource_permissions(user_id: int, resource_type: str, db: Session = deps.get_db) -> List[ModelHasResourcePermission]:
    """
    Fetches the resource permissions of a user.

    :param user_id: The user ID.
    :param db: The database session.
    :return: A list of ResourcePermission objects.
    """
    models = [{"model_type": "users", "model_id": user_id}]
    
    workspaces = get_user_workspaces(user_id, db)
    
    for workspace in workspaces:
        models.append({"model_type": "workspaces", "model_id": workspace.id})
    
    return (
        db.query(ModelHasResourcePermission)
        .filter(ModelHasResourcePermission.model_type.in_([model["model_type"] for model in models]))
        .filter(ModelHasResourcePermission.model_id.in_([model["model_id"] for model in models]))
        .filter(ModelHasResourcePermission.resource_type == resource_type)
        .all()
    )

def get_organization_admins(db: Session) -> List[User]:
    """
    Retrieves the admin user of every organization.

    Crowd analytics is the object of the PID Gijón contract, so it must not be gated
    behind a commercial permission: every organization's admin is processed. The
    permission-filtered variant this replaced returned an empty list whenever the
    deployment held no "crowd_monitoring_advanced" contract, silently disabling the ETL.
    """
    admin_ids = [admin for (admin,) in db.query(Organization.admin).all() if admin]

    if not admin_ids:
        return []

    return db.query(User).filter(User.id.in_(admin_ids)).all()
