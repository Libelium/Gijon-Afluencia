from sqlalchemy import Boolean, Column, Integer, String, DateTime
from sqlalchemy.sql import func
from db.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String)
    last_activity = Column(DateTime)
    organization_id = Column(Integer)
    keycloak_client_id = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    class Config:
        orm_mode = True
