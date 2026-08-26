from db.session import Base
from sqlalchemy import Column, Enum, Integer, String, DateTime, func


class WorkspaceHasUser(Base):
    """
    The permissions of the system
    """

    __tablename__ = "workspace_has_users"

    workspace_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, primary_key=True, index=True)

    class Config:
        orm_mode = True