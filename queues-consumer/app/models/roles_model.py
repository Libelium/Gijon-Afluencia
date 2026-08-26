from db.session import Base
from sqlalchemy import Column, Enum, Integer, String, DateTime, func


class Role(Base):
    """
    The role of the system
    """

    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    guard_name = Column(String)
    organization_id = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    class Config:
        orm_mode = True