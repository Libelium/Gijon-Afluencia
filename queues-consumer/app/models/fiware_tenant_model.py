from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from db.session import Base


class FiwareTenant(Base):
    __tablename__ = "fiware_tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    class Config:
        orm_mode = True
