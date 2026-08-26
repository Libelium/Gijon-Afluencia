from pydantic import BaseModel
from typing import List, Optional
from aether_pylib.context_broker.update_entities_result import EntityBatchOperationError

class DeleteEntitiesResult(BaseModel):
    """
    Delete entity result (Generic for every context broker)
    """

    entities: List[str]
    errors: Optional[List[EntityBatchOperationError]] = None