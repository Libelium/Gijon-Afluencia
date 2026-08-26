from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from db.session import Base
from sqlalchemy.dialects.postgresql import JSONB

class MappingSchema(Base):
    __tablename__ = "mapping_schemas"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String)
    map = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    class Config:
        orm_mode = True


    def __repr__(self):
       return (
           f"<MappingSchema(id={self.id}, name='{self.name}', "
           f"map={self.map}, created_at={self.created_at}, "
           f"updated_at={self.updated_at})>"
       )