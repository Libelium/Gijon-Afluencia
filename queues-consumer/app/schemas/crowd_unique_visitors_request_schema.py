from pydantic import BaseModel, PositiveInt, field_validator
from typing import Literal, Optional, List
from datetime import datetime
import pandas as pd
import numpy as np

class CrowdUniqueVisitorsEntity(BaseModel):
    """
    A request schema for the process visitors etl
    """

    id: int
    tenant: str
    scope: str
    urn: str

class CrowdUniqueVisitorsRequest(BaseModel):
    """
    A request schema for the process visitors etl
    """

    entities: list[CrowdUniqueVisitorsEntity]
    end_date: datetime
    aggregation_mode: Optional[Literal["Daily"] | Literal["Weekly"] | Literal["Biweekly"] | Literal["Monthly"]] = "Daily"
    user_id: PositiveInt
    force: Optional[bool] = False
    
class AllCrowdUniqueVisitorsRequest(BaseModel):
    """
    A request schema for the process visitors etl
    """
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    organization_id: Optional[int] = None
    force: Optional[bool] = False