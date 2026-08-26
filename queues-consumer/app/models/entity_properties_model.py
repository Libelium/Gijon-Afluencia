from enum import Enum
from sqlalchemy import Boolean, Column, Integer, String, DateTime
from sqlalchemy.sql import func
from db.realtime import RealtimeBase
from pydantic import BaseModel

class MeasureType(Enum):
    STRING = "string"
    DOUBLE = "double"
    BOOL = "bool"
  
class EntityProperty(RealtimeBase):
    __tablename__ = "entity_properties"

    id = Column(Integer, primary_key=True, index=True)
    urn = Column(String)
    tenant = Column(String)
    entity_id = Column(Integer)
    scope = Column(String)
    name = Column(String)
    value = Column(String)
    value_type = Column(String)
    units = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    class Config:
        orm_mode = True