from typing import List, Optional
from pydantic import BaseModel


class AutoSubscriptionRequestSchema(BaseModel):
    """
    A request for an auto subscription sync job,
    if no organizations are provided, all organizations will be synced
    if they have the subscriptionAutoSync preference enabled
    """

    organizations: List[int]
    create_new_subscriptions: Optional[bool] = True
    types: Optional[List[str]] = []
    user_id: Optional[int] = None
