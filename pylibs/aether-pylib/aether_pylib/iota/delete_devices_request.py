from pydantic import BaseModel
from typing import List


class DeleteDevicesRequest(BaseModel):
    """
    Delete devices request (Generic for every iota)
    """

    devices_serials: List[str]
