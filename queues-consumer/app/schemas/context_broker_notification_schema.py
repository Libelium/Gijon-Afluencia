import json
from pydantic import BaseModel

class ContextBrokerNotification(BaseModel):
    """
    Helper class to represent a context broker notification, 
    with all the data needede to process it.
    """
    headers: dict
    body: dict