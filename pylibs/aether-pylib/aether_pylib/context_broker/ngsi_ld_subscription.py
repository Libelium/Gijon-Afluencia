from enum import Enum
from pydantic import BaseModel
from typing import List, Optional


class NgsiLdFormat(str, Enum):
    """
    NGSI LD format
    """

    NORMALIZED = "normalized"
    CONCISE = "concise"
    KEY_VALUES = "keyValues"


class NotificationStatus(str, Enum):
    """
    NGSI LD notification status
    """

    OK = "ok"
    FAILED = "failed"


class EntitySelector(BaseModel, extra="allow"):
    """
    Entity selector (ngsi ld spec)
    """

    id: Optional[str] = None
    idPattern: Optional[str] = None
    type: str


class Endpoint(BaseModel, extra="allow"):
    """
    Endpoint (ngsi ld spec)
    """

    uri: str
    accept: str


class NotificationParams(BaseModel, extra="allow"):
    """
    Notification params (ngsi ld spec)
    """

    attributes: Optional[List[str]] = None
    sysAttrs: Optional[bool] = None
    format: NgsiLdFormat
    showChanges: Optional[bool] = None
    endpoint: Endpoint
    status: Optional[str] = None


class NgsiLdSubscription(BaseModel, extra="allow"):
    """
    NGSI LD subscription
    Only used fields are present, feel free to add more if needed
    """

    id: str = None
    type: str = None
    throttling: int = None
    subscriptionName: str = None
    description: str = None
    entities: List[EntitySelector] = None
    notification: NotificationParams = None
