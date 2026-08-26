from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float
from sqlalchemy.sql import func
from db.session import Base


class CustomDatamodel(Base):
    __tablename__ = "custom_datamodels"

    id = Column(Integer, primary_key=True, index=True)
    command = Column(String, nullable=False)
    name = Column(String, nullable=True)
    description = Column(String, nullable=True)
    operations = Column(String, nullable=True)
    data_types = Column(String, nullable=True)
    units = Column(String, nullable=True)
    min = Column(Float, nullable=True)
    max = Column(Float, nullable=True)
    internal = Column(Boolean, default=False)
    firmware_version = Column(String, nullable=True)
    resource_type = Column(String, nullable=True)
    resource_id = Column(Integer, nullable=True)
    template = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    class Config:
        orm_mode = True
