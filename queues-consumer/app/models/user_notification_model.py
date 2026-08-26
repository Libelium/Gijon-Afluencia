from sqlalchemy import Boolean, Column, Integer, String, DateTime
from sqlalchemy.sql import func
from db.realtime import RealtimeBase
from sqlalchemy.dialects.postgresql import JSONB


class UserNotification(RealtimeBase):
    __tablename__ = "user_notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    data = Column(JSONB)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    class Config:
        orm_mode = True
