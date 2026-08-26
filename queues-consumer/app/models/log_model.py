from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from db.session import Base
from sqlalchemy.dialects.postgresql import JSONB


class Log(Base):
    __tablename__ = "log_lines"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    message = Column(String)
    level_name = Column(String)
    datetime = Column(DateTime(timezone=True))
    extra = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    resource_type = Column(String)
    resource_id = Column(Integer)

    class Config:
        orm_mode = True