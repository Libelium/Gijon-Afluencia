from db.session import Base
from sqlalchemy import Column, Enum, Integer, String, DateTime, func


class Permission(Base):
    """
    The permissions of the system
    """

    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    guard_name = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    class Config:
        orm_mode = True