from abc import ABC, abstractmethod
from schemas.context_broker_notification_schema import ContextBrokerNotification

from datetime import datetime

from schemas.entity_data_notification import DataNotification, EntityDataNotification


class CBNotificationTranslator(ABC):
    """
    Context broker notification translator interface.
    It is used to translate context broker notifications
    into the format that Platform understands.
    """

    @abstractmethod
    def translate(
        self, notification: ContextBrokerNotification
    ) -> DataNotification:
        """
        This method translates context broker notifications
        into Platform data notifications.
        The notification should be the body of the notification received,
        and the headers should be the headers of the notification received
        without any modification.

        Translators should not fill the db_id field of the EntityDataNotification,
        as it is the responsibility of the EntitySync job to fill it.
        """
        pass

    @abstractmethod
    def translate_entity(
        self, entity: dict, default_timestamp: datetime, tenant: str, scope: str
    ) -> EntityDataNotification:
        """
        This method translates a single NGSI-LD normalized entity
        into a Platform data notification.
        WARNING: It does not fill the db_id.
        """

        pass
