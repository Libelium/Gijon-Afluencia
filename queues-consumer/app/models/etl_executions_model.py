from sqlalchemy import Boolean, Column, Integer, String, DateTime, JSON, Date
from sqlalchemy.sql import func
from db.session import Base


class ETLExecution(Base):
    __tablename__ = "etl_executions"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    type = Column(String, nullable=False)  # ETL type
    user_id = Column(Integer, nullable=True)
    execution_date = Column(Date, nullable=True)
    params = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    class Config:
        orm_mode = True
