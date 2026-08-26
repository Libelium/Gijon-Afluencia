from pydantic import BaseModel, PositiveInt, field_validator
from typing import Literal, Optional
from datetime import datetime


class ProcessVisitorsEntity(BaseModel):
    """
    A request schema for the process visitors etl
    """

    id: int
    tenant: str
    scope: str
    urn: str
    name: Optional[str] = None


class ProcessVisitorsRequest(BaseModel):
    """
    A request schema for the process visitors etl
    """

    entities: list[ProcessVisitorsEntity]
    start_date: datetime
    end_date: datetime
    mode: Optional[Literal["tourism"]] = "tourism"
    aggregation_mode: Optional[Literal["hourly"] | Literal["none"]] = "none"
    user_id: PositiveInt
    force: Optional[bool] = False


class AllProcessVisitorsRequest(BaseModel):
    """
    A request schema for the process visitors etl
    """

    start_date: Optional[datetime]
    end_date: Optional[datetime]
    organization_id: Optional[int] = None
    force: Optional[bool] = False
