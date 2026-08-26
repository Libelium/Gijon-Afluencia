from typing import Dict, List, Optional, Union
from pydantic import BaseModel


class EntityBatchOperationError(BaseModel):
    """
    Entity update error
    """

    # id of the entity that failed to be updated
    id: str

    # error message
    error: Union[str, Dict]


class UpdateEntitiesResult(BaseModel):
    """
    Result of the update entities operation
    """

    # list of ids of the entities updated (generally it will be the URN in NGSI-LD)
    updated: List[str]
    errors: Optional[List[EntityBatchOperationError]] = None
