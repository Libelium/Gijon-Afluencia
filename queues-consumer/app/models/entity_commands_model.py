from enum import Enum
from sqlalchemy import Boolean, Column, Integer, String, DateTime
from sqlalchemy.sql import func
from db.realtime import RealtimeBase
from pydantic import BaseModel

class EntityCommand(RealtimeBase):
    __tablename__ = "entity_commands"

    id = Column(Integer, primary_key=True, index=True)
    urn = Column(String)
    tenant = Column(String)
    scope = Column(String)
    entity_id = Column(Integer)
    name = Column(String)
    status = Column(String)
    info = Column(String)
    available  = Column(Boolean)
    pending = Column(Boolean)
    pending_value = Column(String)
    status_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    info_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    class Config:
        orm_mode = True