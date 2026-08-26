from pydantic import BaseModel, PositiveInt
from typing import Optional
from datetime import datetime


class CrowdDataCacheETLEntity(BaseModel):
    """
    A request schema for the CrowdDataCache etl
    """

    id: int
    tenant: str
    scope: str
    urn: str
    name: Optional[str] = None


class CrowdDataCacheETLRequest(BaseModel):
    """
    A request schema for the CrowdDataCache etl
    """

    entities: list[CrowdDataCacheETLEntity]
    start_date: datetime
    end_date: datetime
    user_id: PositiveInt
    force: Optional[bool] = False


class AllCrowdDataCacheETLRequest(BaseModel):
    """
    A request schema for the CrowdDataCache etl
    """

    start_date: Optional[datetime]
    end_date: Optional[datetime]
    organization_id: Optional[int] = None
    force: Optional[bool] = False
