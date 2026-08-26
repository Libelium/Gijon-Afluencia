from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from db.session import Base


class DebugLog(Base):
    __tablename__ = "debug_log"

    id = Column(Integer, primary_key=True, index=True)
    cloud_area = Column(String)
    name = Column(String)
    tags = Column(String)
    info = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    class Config:
        orm_mode = True