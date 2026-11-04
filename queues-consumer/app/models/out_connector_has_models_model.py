from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from db.session import Base


class OutConnectorHasModels(Base):
    __tablename__ = "out_connectors_has_models"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    out_connector_id = Column(Integer)
    model_type = Column(String)
    model_id = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    class Config:
        orm_mode = True
