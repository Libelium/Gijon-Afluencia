from pydantic import BaseModel
from typing import List, Optional, Union, Dict


class DeviceBatchOperationError(BaseModel):
    """
    Entity update error
    """

    # id of the entity that failed to be updated
    id: str

    # error message
    error: Union[str, Dict]

class DeleteDevicesResult(BaseModel):
    """
    Delete device result (Generic for every iota)
    """

    devices: List[str]
    errors: Optional[List[DeviceBatchOperationError]] = None