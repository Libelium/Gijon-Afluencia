from db.session import Base
from sqlalchemy import Column, Enum, Integer, String, DateTime, func, Boolean


class Workspace(Base):
    """
    The permissions of the system
    """

    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(String)
    user_id = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    collaborative = Column(Boolean)

    class Config:
        orm_mode = True