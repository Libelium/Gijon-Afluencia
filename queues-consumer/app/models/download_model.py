from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from db.session import Base


class DownloadStatus(str, Enum):
    PENDING = "Pending"
    READY = "Ready"
    FAILED = "Failed"


class Download(Base):
    __tablename__ = "downloads"

    id = Column(Integer, primary_key=True, index=True)
    downloadable_type = Column(String)
    downloadable_id = Column(Integer)
    user_id = Column(Integer)
    file_name = Column(String)
    file_extension = Column(String)
    downloaded = Column(Boolean)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    status = Column(String)

    class Config:
        orm_mode = True
