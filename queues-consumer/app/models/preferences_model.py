from db.session import Base
from sqlalchemy import Column, Enum, Integer, String, DateTime, func


class PreferenceType(str, Enum):
    """
    Some names of preferences, so
    it is centralized here when we call it
    in the rest of the code
    """

    MAIN_SCOPE = "mainScope"
    PLATFORM_DATA_SCOPE = "platformDataScope"
    SUBSCRIPTION_AUTO_SYNC = "subscriptionAutoSync"
    LANGUAGE = "language"


class Preference(Base):
    """
    The preferences of the system, with their default values
    """

    __tablename__ = "preferences"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    default_value = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    class Config:
        orm_mode = True


class Preferencable(Base):
    """
    These are the user preferences
    """

    __tablename__ = "preferencables"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    preference_id = Column(Integer)
    value = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class OrganizationPreference(Base):
    """
    These are the organization preferences
    """

    __tablename__ = "organization_preference"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer)
    preference_id = Column(Integer)
    value = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    class Config:
        orm_mode = True
