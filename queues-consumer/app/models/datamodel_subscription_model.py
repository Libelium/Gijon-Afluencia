from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from geoalchemy2 import Geography
from db.session import Base


class DatamodelSubscription(Base):
    __tablename__ = "datamodel_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    datamodel = Column(String)
    fiware_scope_id = Column(Integer)
    image = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    class Config:
        orm_mode = True
