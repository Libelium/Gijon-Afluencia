from enum import Enum
from typing import List
from db.session import Base
from sqlalchemy import Column, Integer, String, DateTime, func


class ResourcePermissionType(str, Enum):
    """
    An enum with the possible types of permissions for a resource,
    this should be stored in the database (resource_permissions table),
    and is managed through laravel, but we might need it here too.
    """

    READ = "read"
    UPDATE = "update"

    def default_permissions() -> List:
        return [ResourcePermissionType.READ.value, ResourcePermissionType.UPDATE.value]


class ResourcePermission(Base):
    """
    General permissions a resource can have in the system.
    """

    __tablename__ = "resource_permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    class Config:
        orm_mode = True


class ModelHasResourcePermission(Base):
    """
    A bridge table to link users to resources and their permissions.
    """

    __tablename__ = "model_has_resource_permissions"

    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer)
    model_type = Column(String)
    resource_permission_id = Column(Integer)
    resource_type = Column(String)
    resource_id = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    class Config:
        orm_mode = True
