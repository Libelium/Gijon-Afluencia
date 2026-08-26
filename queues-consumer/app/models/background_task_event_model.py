from sqlalchemy import Column, Integer, BigInteger, String, DateTime
from db.realtime import RealtimeBase


class BackgroundJobStep(RealtimeBase):
    __tablename__ = "background_jobs_steps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    background_job_id = Column(BigInteger, nullable=False, index=True)
    name = Column(String, nullable=True)   
    status = Column(String, nullable=False)
    order = Column(Integer, nullable=True) 
    created_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    class Config:
        orm_mode = True
