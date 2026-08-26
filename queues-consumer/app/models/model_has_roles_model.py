from db.session import Base
from sqlalchemy import Column, Enum, Integer, String, DateTime, func


class ModelHasRole(Base):
    """
    The model_has_roles of the system
    """

    __tablename__ = "model_has_roles"

    role_id = Column(Integer, primary_key=True, index=True)
    model_type = Column(String, primary_key=True, index=True)
    model_id = Column(Integer, primary_key=True, index=True)

    class Config:
        orm_mode = True