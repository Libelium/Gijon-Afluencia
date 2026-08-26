from abc import ABC, abstractmethod
from typing import List

from schemas.entity_data_notification import EntityDataNotification


class MappingSchema(ABC):
    """
    Abstract base class representing a schema used to map and transform 
    entity notifications into virtualized versions for different destination entities.

    Implementations of this class must define how the mapping is applied.
    """

    @abstractmethod
    def apply(self, notification: EntityDataNotification) -> List[EntityDataNotification]:
        """
        Transforms the input notification into one or more virtualized notifications 
        by applying a specific mapping strategy.

        Args:
            notification: The original entity data notification to be transformed.

        Returns:
            A list of virtualized EntityDataNotification instances,
            typically targeted at other entities defined by the mapping logic.
        """
        pass
    