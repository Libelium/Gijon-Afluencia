from typing import Dict, List
from aether_pylib.context_broker.update_entities_request import Attribute
from pydantic import BaseModel


class EntityCreate(BaseModel):
    """
    Entity create request
    """

    id: str
    type: str
    attributes: Dict[str, Attribute]


class CreateEntitiesRequest(BaseModel):
    """
    Create entity request (Generic for every context broker)
    """

    entities: List[EntityCreate]
