from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple, Union

import requests
from app.core.configurable_service.configurable_service import ServiceParamDescription

from app.core.context_broker.context_broker_proxy.context_broker_proxy import (
    ContextBrokerProxy,
)
from app.core.context_broker.context_broker_proxy.orion_v2_proxy.crud import (
    types_crud,
    sub_crud,
    entity_crud,
    utils,
)
from aether_pylib.context_broker.create_entities_request import (
    CreateEntitiesRequest,
    EntityCreate,
)
from aether_pylib.context_broker.create_entities_result import (
    CreateEntitiesResponse,
)
from aether_pylib.context_broker.ngsi_ld_subscription import (
    EntitySelector,
    NgsiLdSubscription,
)
from app.core.config.logging import appLogging as logging
from aether_pylib.context_broker.ngsi_v2_subscription import NgsiV2Subscription
from aether_pylib.context_broker.update_entities_request import (
    Attribute,
    AttributeType,
    EntityUpdate,
    UpdateEntitiesRequest,
)
from aether_pylib.context_broker.update_entities_result import (
    EntityBatchOperationError,
    UpdateEntitiesResult,
)

from aether_pylib.context_broker.delete_entities_result import (
    EntityBatchOperationError,
    DeleteEntitiesResult,
)
from aether_pylib.context_broker.delete_entities_request import (
    DeleteEntitiesRequest,
)


class OrionV2Proxy(ContextBrokerProxy):
    """
    Orion-V2 proxy
    """

    def __init__(self, **kwargs):
        """
        Initialize the service. Needed parameters should match kwargs_description
        method.
        """
        self.orion_v2_service = kwargs["ORION_V2_SERVICE"]
        self.platform_subscription_consumer = kwargs["PLATFORM_SUBSCRIPTION_CONSUMER"]
        self.sub_description_identifier = (
            kwargs["PLATFORM_SUBSCRIPTION_ID_TEXT"] or "[Platform]"
        )
        self.sub_ids = (
            {}
        )  # this is a dict of touples (tenant, scope) -> subscription_id
        if self.orion_v2_service is None or self.platform_subscription_consumer is None:
            raise Exception(
                "Missing required parameters.\n" + str(self.params_description())
            )

    def params_description() -> ServiceParamDescription:
        """
        Description of the needed kwargs
        """
        return {
            "ORION_V2_SERVICE": {
                "description": "orionv2 service url",
                "type": str,
                "required": True,
                "default": "",
            },
            "PLATFORM_SUBSCRIPTION_CONSUMER": {
                "description": "URL of the platform subscription consumer",
                "type": str,
                "required": True,
                "default": "",
            },
            "PLATFORM_SUBSCRIPTION_ID_TEXT": {
                "description": "Text to identify the platform subscriptions (this text should be found in the description)",
                "type": str,
                "required": False,
                "default": "[Platform]",
            },
        }

    def __find_platform_sub(self, tenant: str, scope: str) -> NgsiV2Subscription:
        """
        Find the subscription id for the platform.
        This is the subscription that will be used to send notifications to the platform
        It also caches the sub id for future use
        """

        sub_id = self.sub_ids.get((tenant, scope), None)
        if sub_id is not None:
            return sub_crud.get_sub(self.orion_v2_service, tenant, scope, sub_id)

        subs = sub_crud.get_subs(self.orion_v2_service, tenant, scope)
        for sub in subs:
            if self.sub_description_identifier in sub.description:
                self.sub_ids[(tenant, scope)] = sub.id
                return sub

        return None

    def health_check(self) -> bool:
        """
        Return true if the service is ready to be used, throw an exception otherwise
        """
        session = requests.Session()
        response = session.get(self.orion_v2_service + "/version", timeout=5)
        if response.status_code != 200:
            raise Exception(
                f"Orion-v2 service is not available: {response.status_code}"
            )
        return True

    def list_data_types(self, tenant: str, scope: str) -> List[str]:
        """
        List the data types of the Context Broker
        """

        raw_types = types_crud.get_types(self.orion_v2_service, tenant, scope)

        types = []
        for item in raw_types:
            types.append(item["type"])

        return types

    def __get_platform_sub_subject(self, types: List[str]):
        """
        Get the subject of the platform subscription.
        This is intended to subscribe to any entity of the given types,
        regardless of the entity id or the entity attributes
        """
        return {
            "entities": [
                {
                    "idPattern": ".*",
                    "type": entity_type,
                }
                for entity_type in types
            ],
        }

    def __get_new_platform_sub(
        self, types: List[str], tenant: str, scope: str
    ) -> NgsiV2Subscription:
        return NgsiV2Subscription(
            **{
                "description": f"{self.sub_description_identifier} Platform main subscription",
                "subject": self.__get_platform_sub_subject(types),
                "notification": {
                    "http": {
                        "url": self.platform_subscription_consumer,
                    },
                },
            }
        )

    def create_type_subscriptions(
        self, types: List[str], tenant: str, scope: str
    ) -> bool:
        """
        Create a subscription in the Context Broker for a given data type
        """
        if len(types) == 0:
            logging.warning("No types to subscribe to")
            return True

        # first, check if the subscription already exists
        sub = self.__find_platform_sub(tenant, scope)
        if sub is None:
            # create new subscription
            new_sub = self.__get_new_platform_sub(types, tenant, scope)
            new_sub_id = sub_crud.create_sub(
                self.orion_v2_service, tenant, scope, new_sub
            )
            if new_sub_id is None:
                logging.error("Error creating subscription")
                return False
            self.sub_ids[(tenant, scope)] = new_sub_id

        else:
            # update subscription with new types
            return sub_crud.patch_sub(
                self.orion_v2_service,
                tenant,
                scope,
                sub.id,
                NgsiV2Subscription(
                    **{
                        "subject": self.__get_platform_sub_subject(
                            types + self.__get_subs_entity_types(sub)
                        ),
                    }
                ),
            )

        return True

    def delete_type_subscriptions(
        self, types: List[str], tenant: str, scope: str
    ) -> bool:
        """
        Delete a subscription in the Context Broker for a given data type
        """
        if len(types) == 0:
            logging.warning("No types to unsubscribe from")
            return True

        sub = self.__find_platform_sub(tenant, scope)
        if sub is None:
            # nothing to delete
            return True

        # delete types in sub with patch
        new_types = [
            entity.type for entity in sub.subject.entities if entity.type not in types
        ]

        if len(new_types) == 0:
            # delete the subscription
            ok = sub_crud.delete_sub(self.orion_v2_service, tenant, scope, sub.id)
            if ok:
                self.sub_ids.pop((tenant, scope))
            return ok

        return sub_crud.patch_sub(
            self.orion_v2_service,
            tenant,
            scope,
            sub.id,
            NgsiV2Subscription(
                **{
                    "subject": self.__get_platform_sub_subject(new_types),
                }
            ),
        )

    def __get_subs_entity_types(self, sub: NgsiV2Subscription) -> List[str]:
        """
        Returns the entity types of a subscription
        (the types of the entities that will trigger the subscription)
        """
        if sub is None or sub.subject is None or sub.subject.entities is None:
            return []

        return [entity.type for entity in sub.subject.entities]

    def list_type_subscriptions(self, tenant: str, scope: str) -> List[str]:
        """
        List the platform subscriptions in the Context Broker
        """

        sub = self.__find_platform_sub(tenant, scope)
        return self.__get_subs_entity_types(sub)

    def update_entities(
        self, request: UpdateEntitiesRequest, tenant: str, scope: str
    ) -> UpdateEntitiesResult:
        """
        Update an entity in the Context Broker, only if it exists. It can create new attributes
        but not new entities
        """

        updated = set()
        errors = []
        cmds_to_batch = []
        attrs_to_batch = []

        # commands must be sent to batch update, while the others must be done using append
        for entity in request.entities:
            v2_payload = self.__EntityUpdate_to_v2_entity(entity)
            cmds, attrs = self.__split_cmds(v2_payload)
            cmds_to_batch.append(cmds)
            attrs_to_batch.append(attrs)
            logging.info(f"Entity to update: {v2_payload}")
            logging.info(f"Commands to batch: {cmds}")
            logging.info(f"Attributes to batch: {attrs}")

        if len(cmds_to_batch) > 0:
            result = entity_crud.batch_entity_update(
                self.orion_v2_service, cmds_to_batch, tenant, scope
            )
            logging.info(f"Batch update result: {result}")
            if result.errors is not None:
                errors += result.errors
            else:
                updated.update(result.updated)

        if len(attrs_to_batch) > 0:
            result = entity_crud.batch_entity_append(
                self.orion_v2_service, attrs_to_batch, tenant, scope
            )
            logging.info(f"Batch append result: {result}")
            if result.errors is not None and len(result.errors) > 0:
                errors += result.errors
            else:
                updated.update(result.updated)

        return UpdateEntitiesResult(updated=list(updated), errors=errors)

    def get_entity(self, urn: str, tenant: str, scope: str) -> dict:
        """
        Get an entity from the Context Broker, it should return
        the most complete version of the entity
        """
        return entity_crud.get_entity(self.orion_v2_service, urn, tenant, scope)

    def list_entities_by_type(
        self, types: List[str], tenant: str, scope: str,
        limit: int | None = None, offset: int | None = None,
    ) -> List[dict]:
        """
        List all entities of a given type, it should include the most complete version of the entity
        """
        return entity_crud.get_entities(
            self.orion_v2_service, tenant, scope, types,
            limit=limit, offset=offset,
        )

    def create_entities(
        self, request: CreateEntitiesRequest, tenant: str, scope: str
    ) -> CreateEntitiesResponse:
        """
        Create new entities in the Context Broker. It cannot update existing entities, thats why it
        is a loop of create_entity instead of a batch operation.
        """

        created = []
        errors = []

        for entity in request.entities:
            v2_payload = self.__EntityCreate_to_v2_entity(entity)
            result = entity_crud.create_entity(
                self.orion_v2_service, v2_payload, tenant, scope
            )

            if result == None:
                created.append(entity.id)

            else:
                errors.append(EntityBatchOperationError(id=entity.id, error=result))

        return CreateEntitiesResponse(created=created, errors=errors)

    def __EntityCreate_to_v2_entity(self, entity: EntityCreate) -> Dict:
        entity_v2 = {
            "id": entity.id,
            "type": entity.type,
        }

        for key, value in entity.attributes.items():
            entity_v2[key] = self.__Attribute_to_v2_attribute(value)

        return entity_v2

    def __EntityUpdate_to_v2_entity(self, entity: EntityUpdate) -> Dict:
        entity_v2 = {
            "id": entity.id,
        }

        for key, value in entity.attributes.items():
            entity_v2[key] = self.__Attribute_to_v2_attribute(value)

        return entity_v2

    def __Attribute_to_v2_attribute(self, attribute: Attribute) -> Dict:
        if attribute.type == AttributeType.COMMAND:
            return {
                "type": "command",
                "value": attribute.value,
            }

        if attribute.type == AttributeType.RELATIONSHIP:
            return {
                "type": "Relationship",
                "value": attribute.value,
            }

        if attribute.type == AttributeType.PROPERTY:
            return {
                "type": self.__get_property_data_type(attribute.value),
                "value": attribute.value,
            }

    def __get_property_data_type(self, value: Any) -> str:
        if isinstance(value, bool):
            return "Boolean"

        if isinstance(value, str):
            return "Text"

        if isinstance(value, int):
            return "Integer"

        if isinstance(value, float):
            return "Float"

        if isinstance(value, dict):
            # check for geojson
            if "type" in value and value["type"] == "Point":
                return "geo:json"

            return "StructuredValue"

    def __split_cmds(self, entity: Dict) -> Tuple[Dict, Dict]:
        """
        Splits the entity in two, one with the commands and the other with the rest,
        both are complete entities (with id and type)
        """

        cmd_entity = {
            "id": entity["id"],
        }

        normal_entity = {
            "id": entity["id"],
        }

        for key, value in entity.items():
            if isinstance(value, dict) and value.get("type", None) == "command":
                cmd_entity[key] = value
            else:
                normal_entity[key] = value

        return cmd_entity, normal_entity

    def delete_entities(
        self, request: DeleteEntitiesRequest, tenant: str, scope: str
    ) -> DeleteEntitiesResult:
        """
        Delete entities from the Context Broker (Orion V2).
        NOTE: This method is not yet fully implemented for Orion V2.
        """
        
        logging.warning(
            "OrionV2Proxy.delete_entities is called but not fully implemented."
        )

        raise NotImplementedError(
            "Deleting entities is not yet implemented for Orion V2 Context Broker."
        )
