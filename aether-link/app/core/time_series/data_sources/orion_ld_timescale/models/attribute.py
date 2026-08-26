from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON
from sqlalchemy.sql import func
from app.core.time_series.data_sources.orion_ld_timescale.db.session import Base


class Attribute(Base):
    __tablename__ = "attributes"

    instanceid = Column(String, primary_key=True, index=True)
    id = Column(String)
    entityid = Column(Integer, index=True)
    valuetype = Column(String)
    text = Column(String)
    boolean = Column(Boolean)
    number = Column(Integer)
    compound = Column(JSON)
    datetime = Column(DateTime)
    ts = Column(DateTime, index=True)