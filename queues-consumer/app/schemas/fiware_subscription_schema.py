from typing import List, Optional
from pydantic import BaseModel


class TypeSubscriptionMessage(BaseModel):
    """
    Message for the entity type subscription sync job.

    auto_discovery: queries the broker for all available types, overrides subscribe_types.
    create_new_subscriptions: registers new type subscriptions in the broker.
    sync_existing: syncs all subscribed types and re-dispatches even for known entities.
    filter_types: restricts the sync to a subset of subscribed types.
    """

    subscribe_types: Optional[List[str]] = []
    unsubscribe_types: Optional[List[str]] = []
    tenant: str
    scope: str
    auto_discovery: Optional[bool] = False
    sync_existing: Optional[bool] = False
    filter_types: Optional[List[str]] = []
    create_new_subscriptions: Optional[bool] = True
    user_id: Optional[int] = None