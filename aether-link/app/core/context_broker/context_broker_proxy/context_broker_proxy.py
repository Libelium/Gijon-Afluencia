from abc import abstractmethod
from typing import List

from app.core.configurable_service.configurable_service import ConfigurableService
from aether_pylib.context_broker import create_entities_result
from aether_pylib.context_broker.delete_entities_result import DeleteEntitiesResult
from aether_pylib.context_broker.create_entities_request import (
    CreateEntitiesRequest,
)
from aether_pylib.context_broker.update_entities_request import (
    UpdateEntitiesRequest,
)
from aether_pylib.context_broker.delete_entities_request import (
    DeleteEntitiesRequest,
)
from aether_pylib.context_broker.update_entities_result import UpdateEntitiesResult


class ContextBrokerProxy(ConfigurableService):
    """
    Generic Context Broker proxy
    """

    @abstractmethod
    def list_data_types(self, tenant: str, scope: str) -> List[str]:
        """
        List the data types of the Context Broker
        """
        pass

    @abstractmethod
    def create_type_subscriptions(
        self, types: List[str], tenant: str, scope: str
    ) -> bool:
        """
        Create a subscription in the Context Broker for a given data type
        """
        pass

    @abstractmethod
    def delete_type_subscriptions(
        self, types: List[str], tenant: str, scope: str
    ) -> bool:
        """
        Delete a subscription in the Context Broker for a given data type
        """
        pass

    @abstractmethod
    def list_type_subscriptions(self, tenant: str, scope: str) -> List[str]:
        """
        List the subscriptions in the Context Broker for a given data type
        """
        pass

    @abstractmethod
    def update_entities(
        self, request: UpdateEntitiesRequest, tenant: str, scope: str
    ) -> UpdateEntitiesResult:
        """
        Update an entity in the Context Broker. It can create new attributes but
        not new entities.
        """
        pass

    @abstractmethod
    def create_entities(
        self, request: CreateEntitiesRequest, tenant: str, scope: str
    ) -> create_entities_result:
        """
        Create new entities in the Context Broker. It can create new entities but
        not new attributes.
        """
        pass

    @abstractmethod
    def delete_entities(self, request: DeleteEntitiesRequest, tenant: str, scope: str) -> DeleteEntitiesResult:
        """
        Delete entities from the Context Broker.
        """
        pass

    @abstractmethod
    def get_entity(self, urn: str, tenant: str, scope: str) -> dict:
        """
        Get an entity from the Context Broker, it should return
        the most complete version of the entity
        """
        pass

    @abstractmethod
    def list_entities_by_type(
        self, types: List[str], tenant: str, scope: str,
        limit: int | None = None, offset: int | None = None,
    ) -> List[dict]:
        """
        List all entities of a given type, it should include the most complete version of the entity.
        Supports optional limit/offset for pagination.
        """
        pass
