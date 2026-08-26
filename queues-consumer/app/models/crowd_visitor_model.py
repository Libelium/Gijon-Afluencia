from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from db.session import Base


class CrowdVisitor(Base):
    __tablename__ = "crowd_visitors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    visitor_type = Column(String)
    visitor_id = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    class Config:
        orm_mode = True
