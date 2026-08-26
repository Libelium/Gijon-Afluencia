from abc import ABC, abstractmethod

from schemas.entity_data_notification import EntityDataNotification


class NotificationProcessor(ABC):

    @abstractmethod
    def process(
        self, notification: EntityDataNotification
    ) -> EntityDataNotification:
        """
        This method processes a notification received from the context broker.
        The update is by reference, so the notification is modified in place,
        nevertheless, the method should return the notification for convenience.
        """
        pass
