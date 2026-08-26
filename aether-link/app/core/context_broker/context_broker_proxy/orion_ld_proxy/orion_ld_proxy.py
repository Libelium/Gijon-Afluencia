from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, List, Union

import requests
from aether_pylib.context_broker.create_entities_request import (
    CreateEntitiesRequest,
)
from aether_pylib.context_broker.create_entities_result import (
    CreateEntitiesResponse,
)
from aether_pylib.context_broker.ngsi_ld_subscription import (
    EntitySelector,
    NgsiLdSubscription,
)
from aether_pylib.context_broker.update_entities_request import (
    AttributeType,
    UpdateEntitiesRequest,
)
from aether_pylib.context_broker.update_entities_result import (
    EntityBatchOperationError,
    UpdateEntitiesResult,
)

from aether_pylib.context_broker.delete_entities_request import DeleteEntitiesRequest
from aether_pylib.context_broker.delete_entities_result import DeleteEntitiesResult


from app.core.config.logging import appLogging as logging
from app.core.configurable_service.configurable_service import ServiceParamDescription
from app.core.context_broker.context_broker_proxy.context_broker_proxy import (
    ContextBrokerProxy,
)
from app.core.context_broker.context_broker_proxy.orion_ld_proxy.crud import (
    entity_crud,
    sub_crud,
    types_crud,
    utils,
)
import dateutil.parser


class OrionLdProxy(ContextBrokerProxy):
    """
    Orion-LD proxy
    """

    __PLATFORM_SUBSCRIPTION_DEFAULT_URN = "urn:ngsi-ld:subscription:platform:main"

    def __init__(self, **kwargs):
        """
        Initialize the service. Needed parameters should match kwargs_description
        method.
        """
        self.__PLATFORM_SUBSCRIPTION_DEFAULT_URN = "urn:ngsi-ld:Subscription:platform:main"
        self.orion_ld_service = kwargs["ORION_LD_SERVICE"]
        self.tenant = kwargs["DEFAULT_TENANT"]
        self.context_url = kwargs["CONTEXT_URL"]
        self.platform_subscription_consumer = kwargs["PLATFORM_SUBSCRIPTION_CONSUMER"]
        self.platform_subscription_urn = kwargs["PLATFORM_SUBSCRIPTION_URN"]
        if (
            self.orion_ld_service is None
            or self.tenant is None
            or self.context_url is None
            or self.platform_subscription_consumer is None
        ):
            raise Exception(
                "Missing required parameters.\n" + str(self.params_description())
            )

        if self.platform_subscription_urn is None:
            self.platform_subscription_urn = self.__PLATFORM_SUBSCRIPTION_DEFAULT_URN

    def params_description() -> ServiceParamDescription:
        """
        Description of the needed kwargs
        """
        return {
            "ORION_LD_SERVICE": {
                "description": "orionld service url",
                "type": str,
                "required": True,
                "default": "",
            },
            "DEFAULT_TENANT": {
                "description": "Tenant of the temporal service",
                "type": str,
                "required": True,
                "default": "",
            },
            "CONTEXT_URL": {
                "description": "URL of the context file",
                "type": str,
                "required": True,
                "default": "",
            },
            "PLATFORM_SUBSCRIPTION_URN": {
                "description": "URN of the platform subscription",
                "type": str,
                "required": False,
                "default": OrionLdProxy.__PLATFORM_SUBSCRIPTION_DEFAULT_URN,
            },
            "PLATFORM_SUBSCRIPTION_CONSUMER": {
                "description": "URL of the platform subscription consumer",
                "type": str,
                "required": True,
                "default": "",
            },
        }

    def health_check(self) -> bool:
        """
        Return true if the service is ready to be used, throw an exception otherwise
        """
        session = requests.Session()
        response = session.get(self.orion_ld_service + "/version", timeout=5)
        if response.status_code != 200:
            raise Exception(f"Orion-LD service is not ready: {response.text}")

        return True

    def list_data_types(self, tenant: str, scope: str) -> List[str]:
        """
        List the data types of the Context Broker
        """
        type_list = types_crud.get_types(
            self.orion_ld_service, tenant, scope, self.context_url
        )
        return type_list.get("typeList", [])

    def create_type_subscriptions(
        self, types: List[str], tenant: str, scope: str
    ) -> bool:
        """
        Create a subscription in the Context Broker for a given data type
        """
        self.tenant = tenant if tenant else self.tenant
        if len(types) == 0:
            return True

        platform_sub = sub_crud.get_sub(
            self.orion_ld_service,
            self.tenant,
            scope,
            self.context_url,
            self.platform_subscription_urn,
        )
        if platform_sub is None:
            logging.info("Creating new subscription in orion-ld")
            platform_sub = self.__create_new_platform_subscription(types, tenant, scope)
            if platform_sub is None:
                logging.error("Error creating subscription in orion-ld")
                return False
            return True

        # check if the subscription contains all the types
        sub_types = [entity.type for entity in platform_sub.entities]

        if set(types) == set(sub_types):
            # nothing to do
            return True

        all_types = set(types + sub_types)
        # update the subscription
        entities = [
            utils.schema_to_json(EntitySelector(type=type)) for type in all_types
        ]

        # update the subscription
        patch = sub_crud.patch_sub(
            self.orion_ld_service,
            self.tenant,
            scope,
            self.context_url,
            platform_sub.id,
            NgsiLdSubscription(entities=entities),
        )
        return patch is not None

    def delete_type_subscriptions(
        self, types: List[str], tenant: str, scope: str
    ) -> bool:
        """
        Delete a subscription in the Context Broker for a given data type
        """
        self.tenant = tenant if tenant else self.tenant
        if len(types) == 0:
            return True

        platform_sub = sub_crud.get_sub(
            self.orion_ld_service,
            self.tenant,
            scope,
            self.context_url,
            self.platform_subscription_urn,
        )

        if platform_sub is None:
            # nothing to do
            return True

        # remove the types from the subscription
        sub_types = [
            entity.type for entity in platform_sub.entities if entity.type not in types
        ]

        # update the subscription
        if len(sub_types) == 0:
            # delete the subscription
            return sub_crud.delete_sub(
                self.orion_ld_service,
                self.tenant,
                scope,
                self.context_url,
                platform_sub.id,
            )

        entities = [
            utils.schema_to_json(EntitySelector(type=type)) for type in sub_types
        ]

        # update the subscription
        patch = sub_crud.patch_sub(
            self.orion_ld_service,
            self.tenant,
            scope,
            self.context_url,
            platform_sub.id,
            NgsiLdSubscription(entities=entities),
        )

        return patch is not None

    def list_type_subscriptions(self, tenant: str, scope: str) -> List[str]:
        """
        List the subscriptions in the Context Broker for a given data type
        """
        self.tenant = tenant if tenant else self.tenant
        platform_subscription = sub_crud.get_sub(
            self.orion_ld_service,
            self.tenant,
            scope,
            self.context_url,
            self.platform_subscription_urn,
        )
        if platform_subscription is None:
            return []
        return self.__get_types_from_subscription(platform_subscription)

    def __get_types_from_subscription(
        self, subscription: NgsiLdSubscription
    ) -> List[str]:
        """
        Return the types of the subscription (subscribed types)
        """
        return [entity.type for entity in subscription.entities]

    def __build_new_platform_subscription(self, types: List[str]) -> NgsiLdSubscription:
        """
        Build a new platform subscription
        """
        return NgsiLdSubscription(
            **{
                "id": self.platform_subscription_urn,
                "type": "Subscription",
                "throttling": -1, 
                "subscriptionName": "PLATFORM-Main-Subscription",
                "description": "Platform main subscription to keep track of all the entities in the system",
                "entities": [{"type": type} for type in types],
                "notification": {
                    "format": "normalized",
                    "endpoint": {
                        "uri": self.platform_subscription_consumer,
                        "accept": "application/json",
                    },
                },
            }
        )

    def __create_new_platform_subscription(
        self, types: List[str], tenant: str, scope: str
    ) -> NgsiLdSubscription:
        """
        Creates the platform subscription in the context broker, if it does not exist,
        for the given types
        """

        new_sub = self.__build_new_platform_subscription(types)

        return sub_crud.create_sub(
            self.orion_ld_service,
            tenant,
            scope,
            self.context_url,
            new_sub,
        )

    def update_entities(
        self, request: UpdateEntitiesRequest, tenant: str, scope: str
    ) -> UpdateEntitiesResult:
        """
        Update an entity in the Context Broker, only if it exists. It can create new attributes
        but not new entities
        """

        self.tenant = tenant if tenant else self.tenant
        json_body = self.__build_entity_operations_body(request)

        params = self.__build_url_params_for_entity_operations_update(request)

        response = entity_crud.update_entities(
            self.orion_ld_service,
            self.tenant,
            scope,
            self.context_url,
            json_body,
            params,
        )

        entity_update_result = self.__build_entity_batch_operation_result(
            request, response
        )

        cmds_by_entity = {
            entity.id: [
                {"name": attr_name, "value": attr_update.value}
                for attr_name, attr_update in entity.attributes.items()
                if attr_update.type == AttributeType.COMMAND
            ]
            for entity in request.entities
        }

        cmds_update_result = entity_crud.send_commands(
            self.orion_ld_service,
            self.tenant,
            scope,
            self.context_url,
            cmds_by_entity,
        )

        # now, merge the results, errors can be repeated, but updated should not
        return UpdateEntitiesResult(
            updated=list(
                set(entity_update_result.updated + cmds_update_result.updated)
            ),
            errors=entity_update_result.errors + cmds_update_result.errors,
        )

    def __build_entity_batch_operation_result(
        self,
        request: Union[UpdateEntitiesRequest, CreateEntitiesRequest],
        response: requests.Response,
    ) -> dict:
        """
        Build the result of the update entities operation
        """

        # check if the operation was successful and build the result
        modified = []
        errors = []

        # everything ok, all entities were updated (or not if noOverwrite is true, but orion
        # does not notify that in case of error)
        if (
            response.status_code == 200
            or response.status_code == 204
            or response.status_code == 201
        ):
            modified = [entity.id for entity in request.entities]

        # multi status response, some entities were updated and some not
        elif response.status_code == 207:
            response_body = response.json()
            modified = response_body.get("success", [])
            errors = [
                EntityBatchOperationError(id=error["entityId"], error=error["error"])
                for error in response_body.get("errors", [])
            ]

        # this should not happen, but who knows with orion-ld
        else:
            logging.error(
                "Unknown error updating entities in orion-ld: "
                + str(response.text)
                + " "
                + str(response.status_code)
            )
            modified = []
            errors = [
                EntityBatchOperationError(
                    id=entity.id,
                    error={
                        "message": "Unknown error updating entity in orion-ld",
                        "status": response.status_code,
                    },
                )
                for entity in request.entities
            ]

        if isinstance(request, CreateEntitiesRequest):
            return CreateEntitiesResponse(created=modified, errors=errors)
        else:
            return UpdateEntitiesResult(updated=modified, errors=errors)

    def __build_url_params_for_entity_operations_update(
        self, request: UpdateEntitiesRequest
    ) -> dict:
        """
        Build the url params of the request to update entities in the Context Broker
        """

        url_params = {}

        if request.noOverwrite:
            url_params["options"] = "noOverwrite"

        return url_params

    def __build_entity_operations_body(
        self, request: Union[UpdateEntitiesRequest, CreateEntitiesRequest]
    ) -> dict:
        """
        Build the body of the request to update entities in the Context Broker.
        This ignores all the attributes of type Command, because they should not be updated
        using the batch update operation (entityOperations/update)
        """

        request_body = []

        include_type = isinstance(request, CreateEntitiesRequest)

        for entity in request.entities:
            entity_body = {"id": entity.id}

            if include_type:
                entity_body["type"] = entity.type

            for attr_name, attr_update in entity.attributes.items():
                # remember that we are ignoring commands because they should not be updated
                # using the batch update operation (it does not trigger the subscription)
                if attr_update.type == AttributeType.COMMAND:
                    continue

                value_key = (
                    "object"
                    if attr_update.type == AttributeType.RELATIONSHIP
                    else "value"
                )

                timestamp = getattr(attr_update, "timestamp", None) or datetime.now(tz=timezone.utc)
                entity_body[attr_name] = {
                    value_key: attr_update.value,
                    "observedAt": dateutil.parser.parse(timestamp.isoformat()).isoformat(),
                }

            request_body.append(entity_body)

        return request_body

    def get_entity(self, urn: str, tenant: str, scope: str) -> dict:
        """
        Get an entity from the Context Broker, it should return
        the most complete version of the entity
        """
        return entity_crud.get_entity(
            self.orion_ld_service, tenant, scope, self.context_url, urn
        )

    def list_entities_by_type(
        self, types: List[str], tenant: str, scope: str,
        limit: int | None = None, offset: int | None = None,
    ) -> List[dict]:
        """
        List all entities of a given type, it should include the most complete version of the entity
        """
        return entity_crud.get_entities(
            self.orion_ld_service, tenant, scope, self.context_url, types,
            limit=limit, offset=offset,
        )

    def create_entities(
        self, request: CreateEntitiesRequest, tenant: str, scope: str
    ) -> CreateEntitiesResponse:
        """
        Create new entities in the Context Broker.
        TODO: make it possible to update entities, this should be changed to an upsert operation
        """

        json_body = self.__build_entity_operations_body(request)

        response = entity_crud.create_entities(
            self.orion_ld_service,
            tenant,
            scope,
            self.context_url,
            json_body,
        )

        entity_create_result = self.__build_entity_batch_operation_result(
            request, response
        )

        return entity_create_result
    
    def delete_entities(self, request: DeleteEntitiesRequest, tenant: str, scope: str) -> DeleteEntitiesResult:
        """
        Delete entity from the Context Broker.
        """
        response = entity_crud.delete_entities(
            self.orion_ld_service,
            tenant,
            scope,
            self.context_url,
            request.entities_urn,
        )
        
        return response

        
    def delete_entity_attribute(
        self, entity_id: str, attr_name: str, tenant: str, scope: str
    ) -> dict:
        """
        Delete an attribute from an entity in the Context Broker.
        Returns a dict with the result of the operation.
        """
        self.tenant = tenant if tenant else self.tenant
        response = entity_crud.delete_entity_attribute(
            self.orion_ld_service,
            self.tenant,
            scope,
            self.context_url,
            entity_id,
            attr_name,
        )

        if response.status_code == 204:
            return {"deleted": attr_name, "entityId": entity_id}
        elif response.status_code == 404:
            return {"error": "Entity or attribute not found", "status": 404}
        else:
            logging.error(
                f"Error deleting attribute {attr_name} from entity {entity_id}: "
                + str(response.text)
            )
            return {"error": response.text, "status": response.status_code}
