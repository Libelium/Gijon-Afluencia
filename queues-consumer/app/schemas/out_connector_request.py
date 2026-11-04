from typing import Dict
from schemas.entity_data_notification import EntityDataNotification
from pydantic import BaseModel

class OutConnectorRequest(BaseModel):
    """
    A request to an out connector
    """

    notification: EntityDataNotification
    # a dictionary with connector data, so we can serialize it
    out_connector: Dict
