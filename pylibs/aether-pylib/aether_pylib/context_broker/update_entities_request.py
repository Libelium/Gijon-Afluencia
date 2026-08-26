from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel


class AttributeType(str, Enum):
    RELATIONSHIP = "Relationship"
    PROPERTY = "Property"
    COMMAND = "Command"


class Attribute(BaseModel):
    """
    Attribute update request
    """

    type: AttributeType
    value: Any
    timestamp: Optional[datetime] = None


class EntityUpdate(BaseModel):
    """
    Entity update request
    """

    id: str
    attributes: Dict[str, Attribute]


class UpdateEntitiesRequest(BaseModel):
    """
    Update entity request (Generic for every context broker)
    """

    noOverwrite: Optional[bool] = False
    entities: List[EntityUpdate]
