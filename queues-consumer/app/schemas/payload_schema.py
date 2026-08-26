from pydantic import BaseModel, RootModel
from typing import Dict, Any, Optional
from datetime import datetime


class LegacyPayload(BaseModel):
    timestamp: str
    value: Any
    urn: str
    tenant: str
    scope: str
    measure: str
    unit: Optional[str] = None


class NormalizedValue(BaseModel):
    value: Any
    type: str
    ts: datetime
    metadata: Dict[str, Any]


class NormalizedPayload(RootModel):
    root: Dict[str, NormalizedValue]


class KeyValuePayload(RootModel):
    root: Dict[str, Any]
