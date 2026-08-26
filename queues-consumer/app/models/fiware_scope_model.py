from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from db.session import Base


class FiwareScope(Base):
    __tablename__ = "fiware_scopes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    fiware_tenant_id = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    class Config:
        orm_mode = True
