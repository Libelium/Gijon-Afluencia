from enum import Enum
from pydantic import BaseModel
from typing import List, Optional


class SubjectEntity(BaseModel, extra="allow"):
    idPattern: str
    type: str


class SubscriptionSubject(BaseModel, extra="allow"):
    entities: List[SubjectEntity]


class HttpNotification(BaseModel, extra="allow"):
    url: str


class SubNotification(BaseModel, extra="allow"):
    http: HttpNotification


class NgsiV2Subscription(BaseModel, extra="allow"):
    """
    NGSI V2 subscription
    Only used fields are present, feel free to add more if needed
    """

    id: str = None
    description: str = None
    subject: SubscriptionSubject = None
    notification: SubNotification = None
