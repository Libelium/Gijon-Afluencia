from pydantic import BaseModel, PositiveInt, field_validator
from typing import Literal, Optional
from datetime import datetime


class CrowdClassificationEntity(BaseModel):
    """
    A request schema for the process visitors etl
    """

    id: int
    tenant: str
    scope: str
    urn: str
    name: Optional[str] = None


class CrowdClassificationRequest(BaseModel):
    """
    A request schema for the process visitors etl
    """

    entities: list[CrowdClassificationEntity]
    start_date: datetime
    end_date: datetime
    mode: Optional[Literal["monthly"]|Literal["weekly"]] = "monthly"
    user_id: PositiveInt
    force: Optional[bool] = False


class AllCrowdClassificationRequest(BaseModel):
    """
    A request schema for the process visitors etl
    """

    start_date: Optional[datetime]
    end_date: Optional[datetime]
    organization_id: Optional[int] = None
    force: Optional[bool] = False


class OneCrowdClassificationRequest(BaseModel):
    user_id: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    force: bool = False
