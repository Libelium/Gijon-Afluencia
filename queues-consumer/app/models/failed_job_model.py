from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from db.session import Base


class FailedJob(Base):
    __tablename__ = "failed_jobs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    connection = Column(Text, nullable=False)
    queue = Column(Text, nullable=False)
    payload = Column(Text, nullable=False)
    exception = Column(Text, nullable=False)
    failed_at = Column(DateTime(timezone=True), server_default=func.now())
    uuid = Column(String)

    class Config:
        orm_mode = True