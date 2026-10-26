from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from db.session import Base

class OutConnectorStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    
class OutConnector(Base):
    __tablename__ = "out_connectors"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String)
    type = Column(String)
    status = Column(String)
    user_id = Column(Integer)
    last_connection = Column(DateTime(timezone=True), nullable=True)
    connectable_type = Column(String)
    connectable_id = Column(Integer)
    retries = Column(Integer)
    use_readable_names = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    class Config:
        orm_mode = True

    def dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
