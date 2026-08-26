from db.session import Base
from sqlalchemy import Column, Integer, String, DateTime, func


class Organization(Base):
    """
    The organization model, which represents an organization in the system.
    """

    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    admin = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    class Config:
        orm_mode = True


class OrganizationHasResource(Base):
    """
    A bridge table between organizations and resources.
    """

    __tablename__ = "organization_has_resource"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer)
    resource_type = Column(String)
    resource_id = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    class Config:
        orm_mode = True
