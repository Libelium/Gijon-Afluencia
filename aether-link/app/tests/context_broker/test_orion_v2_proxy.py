from typing import Any, Dict
from app.core.context_broker.context_broker_proxy.orion_v2_proxy.orion_v2_proxy import (
    OrionV2Proxy,
)
from aether_pylib.context_broker.create_entities_request import EntityCreate
from aether_pylib.context_broker.update_entities_request import (
    Attribute,
    AttributeType,
    EntityUpdate,
)
import pytest


@pytest.fixture
def context_broker_proxy_config():
    return {
        "ORION_V2_SERVICE": "http://orion-ld:1026",
        "DEFAULT_TENANT": "gijon",
        "PLATFORM_SUBSCRIPTION_CONSUMER": "http://platform:8080",
        "PLATFORM_SUBSCRIPTION_ID_TEXT": "[platform]",
    }


@pytest.fixture
def context_broker_proxy(context_broker_proxy_config):
    return OrionV2Proxy(**context_broker_proxy_config)


class TestOrionV2Proxy:

    @pytest.mark.parametrize(
        ("value", "expected_type"),
        [
            (1, "Integer"),
            (1.0, "Float"),
            ("1", "Text"),
            (True, "Boolean"),
            ({}, "StructuredValue"),
            (
                {
                    "type": "Point",
                    "coordinates": [1.0, 2.0],
                },
                "geo:json",
            ),
        ],
    )
    def testPropertyTypeDiscovery(
        self,
        value: Any,
        expected_type: str,
        context_broker_proxy,
    ):
        assert (
            context_broker_proxy._OrionV2Proxy__get_property_data_type(value)
            == expected_type
        )

    @pytest.mark.parametrize(
        ("attribute", "expected_value"),
        [
            (
                Attribute(
                    type=AttributeType.PROPERTY,
                    value=23.0,
                ),
                {
                    "type": "Float",
                    "value": 23.0,
                },
            ),
            (
                Attribute(
                    type=AttributeType.PROPERTY,
                    value="23",
                ),
                {
                    "type": "Text",
                    "value": "23",
                },
            ),
            (
                Attribute(
                    type=AttributeType.PROPERTY,
                    value=True,
                ),
                {
                    "type": "Boolean",
                    "value": True,
                },
            ),
            (
                Attribute(
                    type=AttributeType.RELATIONSHIP,
                    value="urn:ngsi-ld:Device:001",
                ),
                {
                    "type": "Relationship",
                    "value": "urn:ngsi-ld:Device:001",
                },
            ),
            (
                Attribute(
                    type=AttributeType.COMMAND,
                    value="turnOn",
                ),
                {
                    "type": "command",
                    "value": "turnOn",
                },
            ),
        ],
    )
    def testAttributeToV2Attribute(
        self, attribute: Attribute, expected_value: Dict, context_broker_proxy
    ):
        assert (
            context_broker_proxy._OrionV2Proxy__Attribute_to_v2_attribute(attribute)
            == expected_value
        )

    @pytest.mark.parametrize(
        ("entity_create", "expected_entity"),
        [
            (
                EntityCreate(
                    id="urn:ngsi-ld:Device:001",
                    type="Device",
                    attributes={
                        "temperature": Attribute(
                            type=AttributeType.PROPERTY,
                            value=25.0,
                        ),
                        "location": Attribute(
                            type=AttributeType.RELATIONSHIP,
                            value="urn:ngsi-ld:Device:001",
                        ),
                        "command": Attribute(
                            type=AttributeType.COMMAND,
                            value="turnOn",
                        ),
                    },
                ),
                {
                    "id": "urn:ngsi-ld:Device:001",
                    "type": "Device",
                    "temperature": {
                        "type": "Float",
                        "value": 25.0,
                    },
                    "location": {
                        "type": "Relationship",
                        "value": "urn:ngsi-ld:Device:001",
                    },
                    "command": {
                        "type": "command",
                        "value": "turnOn",
                    },
                },
            )
        ],
    )
    def testEntityCreateToV2Entity(
        self, entity_create: EntityCreate, expected_entity: Dict, context_broker_proxy
    ):
        assert (
            context_broker_proxy._OrionV2Proxy__EntityCreate_to_v2_entity(entity_create)
            == expected_entity
        )

    @pytest.mark.parametrize(
        ("entity_update", "expected_entity"),
        [
            (
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
                        "command": Attribute(
                            type=AttributeType.COMMAND,
                            value="turnOn",
                        ),
                    },
                ),
                {
                    "id": "urn:ngsi-ld:Device:001",
                    "temperature": {
                        "type": "Float",
                        "value": 25.0,
                    },
                    "location": {
                        "type": "Relationship",
                        "value": "urn:ngsi-ld:Device:001",
                    },
                    "command": {
                        "type": "command",
                        "value": "turnOn",
                    },
                },
            )
        ],
    )
    def testEntityCreateToV2Entity(
        self, entity_update: EntityUpdate, expected_entity: Dict, context_broker_proxy
    ):
        assert (
            context_broker_proxy._OrionV2Proxy__EntityUpdate_to_v2_entity(entity_update)
            == expected_entity
        )
