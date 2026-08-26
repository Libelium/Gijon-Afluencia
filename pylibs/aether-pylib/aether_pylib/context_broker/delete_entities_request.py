from pydantic import BaseModel
from typing import List


class DeleteEntitiesRequest(BaseModel):
    """
    Delete entity request (Generic for every context broker)
    """

    entities_urn: List[str]
