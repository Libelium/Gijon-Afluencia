from app.core.time_series.data_sources.quantum_leap.models import Base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON


class MdEtsMetadata(Base):
    __tablename__ = "md_ets_metadata"
    __schema__ = "public"

    table_name = Column(String, primary_key=True)
    entity_attrs = Column(JSON)

    class Config:
        orm_mode = True
