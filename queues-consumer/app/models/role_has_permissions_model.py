from db.session import Base
from sqlalchemy import Column, Enum, Integer, String, DateTime, func


class RoleHasPermission(Base):
    """
    The permissions of the system
    """

    __tablename__ = "role_has_permissions"

    permission_id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, primary_key=True, index=True)

    class Config:
        orm_mode = True