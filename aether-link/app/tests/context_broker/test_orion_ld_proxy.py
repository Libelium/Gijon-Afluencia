from typing import List
from unittest.mock import MagicMock, patch
from aether_pylib.context_broker.ngsi_ld_subscription import NgsiLdSubscription
from aether_pylib.context_broker.update_entities_request import (
    AttributeType,
    Attribute,
    EntityUpdate,
    UpdateEntitiesRequest,
)
from aether_pylib.context_broker.delete_entities_result import (
    EntityBatchOperationError,
    DeleteEntitiesResult,
)
from aether_pylib.context_broker.delete_entities_request import (
    DeleteEntitiesRequest,
)
import requests
import pytest

from app.core.context_broker.context_broker_proxy.orion_ld_proxy.orion_ld_proxy import (
    OrionLdProxy,
)
import freezegun


@pytest.fixture
def context_broker_proxy_config():
    return {
        "ORION_LD_SERVICE": "http://orion-ld:1026",
        "DEFAULT_TENANT": "gijon",
        "CONTEXT_URL": "http://context-server/context.jsonld",
        "PLATFORM_SUBSCRIPTION_CONSUMER": "http://platform:8080",
        "PLATFORM_SUBSCRIPTION_URN": "urn:ngsi-ld:Subscription:platform:mainSub",
    }


@pytest.fixture
def context_broker_proxy(context_broker_proxy_config):
    return OrionLdProxy(**context_broker_proxy_config)


def reference_time():
    return "2025-01-01T00:00:00+00:00"


class TestOrionLdProxy:
    @pytest.mark.parametrize(
        ("types"),
        [
            (["Device"]),
            (["Device", "Sensor", "WeatherObserved"]),
        ],
    )
    def test_new_platform_subscription_building(
        self, types: List[str], context_broker_proxy_config, context_broker_proxy
    ):
        new_sub = context_broker_proxy._OrionLdProxy__build_new_platform_subscription(types)

        expected_sub = NgsiLdSubscription(
            **{
                "id": context_broker_proxy_config["PLATFORM_SUBSCRIPTION_URN"],
                "type": "Subscription",
                "subscriptionName": "PLATFORM-Main-Subscription",
                "description": "Description is irrelevant",
                "entities": [{"type": type} for type in types],
                "notification": {
                    "format": "normalized",
                    "endpoint": {
                        "uri": context_broker_proxy_config[
                            "PLATFORM_SUBSCRIPTION_CONSUMER"
                        ],
                        "accept": "application/json",
                    },
                },
            }
        )

        # now compare relevant fields
        assert new_sub.id == expected_sub.id
        assert new_sub.type == expected_sub.type
        assert new_sub.subscriptionName == expected_sub.subscriptionName
        assert new_sub.notification.format == expected_sub.notification.format
        assert new_sub.notification.sysAttrs == expected_sub.notification.sysAttrs
        assert new_sub.notification.showChanges == expected_sub.notification.showChanges
        assert (
            new_sub.notification.endpoint.uri == expected_sub.notification.endpoint.uri
        )
        assert (
            new_sub.notification.endpoint.accept
            == expected_sub.notification.endpoint.accept
        )
        for i in range(len(new_sub.entities)):
            assert new_sub.entities[i].type == expected_sub.entities[i].type

    @pytest.mark.parametrize(
        ("update_request", "expected_body"),
        [
            (
                UpdateEntitiesRequest(
                    entities=[
                        EntityUpdate(
                            id="urn:ngsi-ld:Device:001",
                            attributes={
                                "temperature": Attribute(
                                    type=AttributeType.PROPERTY,
                                    value=25.0,
                                ),
                                "location": Attribute(
                                    type=AttributeType.RELATIONSHIP,
                                    value="urn:ngsi-ld:Device:001",
                                ),
                            },
                        ),
                    ]
                ),
                [
                    {
                        "id": "urn:ngsi-ld:Device:001",
                        "temperature": {
                            "value": 25.0,
                            "observedAt": reference_time(),
                        },
                        "location": {
                            "object": "urn:ngsi-ld:Device:001",
                            "observedAt": reference_time(),
                        },
                    }
                ],
            )
        ],
    )
    @freezegun.freeze_time(reference_time())
    def test_update_entities_body_building(
        self,
        update_request: UpdateEntitiesRequest,
        expected_body: dict,
        context_broker_proxy: OrionLdProxy,
    ):
        body = context_broker_proxy._OrionLdProxy__build_entity_operations_body(
            update_request
        )
        assert body == expected_body

    @pytest.mark.parametrize(
        ("update_request", "expected_params"),
        [
            (
                UpdateEntitiesRequest(noOverwrite=True, entities=[]),
                {"options": "noOverwrite"},
            ),
            (UpdateEntitiesRequest(noOverwrite=False, entities=[]), {}),
            (UpdateEntitiesRequest(entities=[]), {}),
        ],
    )
    def test_update_entities_param_building(
        self,
        update_request: UpdateEntitiesRequest,
        expected_params: dict,
        context_broker_proxy: OrionLdProxy,
    ):
        params = context_broker_proxy._OrionLdProxy__build_url_params_for_entity_operations_update(
            update_request
        )
        assert params == expected_params

    @patch("app.core.context_broker.context_broker_proxy.orion_ld_proxy.crud.entity_crud.delete_entities")
    @pytest.mark.parametrize(
        ("delete_request", "mock_crud_return_value", "expected_result"),
        [
            # Successful deletion
            (
                DeleteEntitiesRequest(entities_urn=["urn:ngsi-ld:Device:001"]),
                DeleteEntitiesResult(entities=["urn:ngsi-ld:Device:001"], errors=[]),
                DeleteEntitiesResult(entities=["urn:ngsi-ld:Device:001"], errors=[]),
            ),
            # Entity not found
            (
                DeleteEntitiesRequest(entities_urn=["urn:ngsi-ld:Device:002"]),
                DeleteEntitiesResult(
                    entities=[],
                    errors=[
                        EntityBatchOperationError(
                            id="urn:ngsi-ld:Device:002",
                            error={"message": "Entity not found", "status": 404},
                        )
                    ],
                ),
                DeleteEntitiesResult(
                    entities=[],
                    errors=[
                        EntityBatchOperationError(
                            id="urn:ngsi-ld:Device:002",
                            error={"message": "Entity not found", "status": 404},
                        )
                    ],
                ),
            ),
            # Multiple deletions: one success, one not found
            (
                DeleteEntitiesRequest(entities_urn=["urn:ngsi-ld:Device:003", "urn:ngsi-ld:Device:004"]),
                DeleteEntitiesResult(
                    entities=["urn:ngsi-ld:Device:003"],
                    errors=[
                        EntityBatchOperationError(
                            id="urn:ngsi-ld:Device:004",
                            error={"message": "Entity not found", "status": 404},
                        )
                    ],
                ),
                DeleteEntitiesResult(
                    entities=["urn:ngsi-ld:Device:003"],
                    errors=[
                        EntityBatchOperationError(
                            id="urn:ngsi-ld:Device:004",
                            error={"message": "Entity not found", "status": 404},
                        )
                    ],
                ),
            ),
            # Generic error
            (
                DeleteEntitiesRequest(entities_urn=["urn:ngsi-ld:Device:005"]),
                DeleteEntitiesResult(
                    entities=[],
                    errors=[
                        EntityBatchOperationError(
                            id="urn:ngsi-ld:Device:005",
                            error={
                                "message": "Error deleting entity: Internal Server Error",
                                "status": 500,
                            },
                        )
                    ],
                ),
                DeleteEntitiesResult(
                    entities=[],
                    errors=[
                        EntityBatchOperationError(
                            id="urn:ngsi-ld:Device:005",
                            error={
                                "message": "Error deleting entity: Internal Server Error",
                                "status": 500,
                            },
                        )
                    ],
                ),
            ),
            # Simulate a request exception from the CRUD layer
            (
                DeleteEntitiesRequest(entities_urn=["urn:ngsi-ld:Device:006"]),
                DeleteEntitiesResult(
                    entities=[],
                    errors=[
                        EntityBatchOperationError(
                            id="urn:ngsi-ld:Device:006",
                            error={
                                "message": "Network or connection error: Connection refused",
                                "status": 500,
                            },
                        )
                    ],
                ),
                DeleteEntitiesResult(
                    entities=[],
                    errors=[
                        EntityBatchOperationError(
                            id="urn:ngsi-ld:Device:006",
                            error={
                                "message": "Network or connection error: Connection refused",
                                "status": 500,
                            },
                        )
                    ],
                ),
            ),
        ],
    )

    def test_delete_entities(
        self,
        mock_delete_entities: MagicMock,
        delete_request: DeleteEntitiesRequest,
        mock_crud_return_value: DeleteEntitiesResult,
        expected_result: DeleteEntitiesResult,
        context_broker_proxy: OrionLdProxy,
    ):
        mock_delete_entities.return_value = mock_crud_return_value
        scopeDefault = "/"
        result = context_broker_proxy.delete_entities(
            delete_request, context_broker_proxy.tenant, scopeDefault
        )

        mock_delete_entities.assert_called_once_with(
            context_broker_proxy.orion_ld_service,
            context_broker_proxy.tenant,
            scopeDefault,
            context_broker_proxy.context_url,
            delete_request.entities_urn,
        )

        assert result == expected_result