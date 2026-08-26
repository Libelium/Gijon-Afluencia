from typing import List, Optional
from aether_pylib.context_broker.update_entities_result import EntityBatchOperationError
from pydantic import BaseModel


class CreateEntitiesResponse(BaseModel):
    """
    Create entity response (Generic for every context broker)
    """

    created: List[str]
    errors: Optional[List[EntityBatchOperationError]] = None
