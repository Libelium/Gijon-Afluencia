from typing import Dict
import pytest
from aether_pylib.iota.iota_provision_payload import DeviceDef
from app.core.iota.iota_proxy.translation.ld_2_v2_translation import (
    ld_2_v2,
    ld_2_v2_static_attributes,
)


class TestTranslations:
    """
    Test translation between Ngsi-Ld and Ngsi-v2
    """

    @pytest.mark.parametrize(
        ("ld_payload", "expected_v2_payload"),
        [
            (
                DeviceDef(
                    **{
                        "device_id": "Device001",
                        "apikey": "testApikey",
                        "transport": "HTTP",
                        "endpoint": "http://sampleEndpoint.com",
                        "attributes": [
                            {
                                "object_id": "m_1",
                                "name": "a_1",
                                "type": "Property",
                                "metadata": {
                                    "unitCode": {"type": "Text", "value": "h"}
                                },
                            }
                        ],
                        "commands": [
                            {"name": "cmd_1", "type": "Property"},
                            {"name": "cmd_2", "type": "Property"},
                        ],
                        "static_attributes": [
                            {
                                "name": "commands",
                                "type": "Property",
                                "value": ["cmd_1", "cmd_2"],
                            }
                        ],
                    }
                ),
                DeviceDef(
                    **{
                        "device_id": "Device001",
                        "apikey": "testApikey",
                        "transport": "HTTP",
                        "endpoint": "http://sampleEndpoint.com",
                        "attributes": [
                            {
                                "object_id": "m_1",
                                "name": "a_1",
                                "type": "Object",
                                "metadata": {
                                    "unitCode": {"type": "Text", "value": "h"}
                                },
                            }
                        ],
                        "commands": [
                            {"name": "cmd_1", "type": "command"},
                            {"name": "cmd_2", "type": "command"},
                        ],
                        "static_attributes": [
                            {
                                "name": "commands",
                                "type": "Array",
                                "value": ["cmd_1", "cmd_2"],
                            }
                        ],
                    }
                ),
            ),
        ],
    )
    def test_device_translation_ld_to_v2(
        self, ld_payload: DeviceDef, expected_v2_payload: DeviceDef
    ):
        """
        Test translation from Ngsi-v2 to Ngsi-Ld
        """
        assert ld_2_v2(ld_payload) == expected_v2_payload

    @pytest.mark.parametrize(
        ("attrribute", "expected_value"),
        [
            (
                {
                    "name": "a_1",
                    "value": "23",
                    "type": "Property",
                    "metadata": {"unitCode": {"type": "Text", "value": "h"}},
                },
                {
                    "name": "a_1",
                    "value": "23",
                    "type": "String",
                    "metadata": {"unitCode": {"type": "Text", "value": "h"}},
                },
            ),
            (
                {
                    "name": "a_1",
                    "value": 23,
                    "type": "Property",
                    "metadata": {"unitCode": {"type": "Text", "value": "h"}},
                },
                {
                    "name": "a_1",
                    "value": 23,
                    "type": "Number",
                    "metadata": {"unitCode": {"type": "Text", "value": "h"}},
                },
            ),
            (
                {
                    "name": "a_1",
                    "value": 23.5,
                    "type": "Property",
                    "metadata": {"unitCode": {"type": "Text", "value": "h"}},
                },
                {
                    "name": "a_1",
                    "value": 23.5,
                    "type": "Number",
                    "metadata": {"unitCode": {"type": "Text", "value": "h"}},
                },
            ),
            (
                {
                    "name": "a_1",
                    "value": True,
                    "type": "Property",
                    "metadata": {"unitCode": {"type": "Text", "value": "h"}},
                },
                {
                    "name": "a_1",
                    "value": True,
                    "type": "Boolean",
                    "metadata": {"unitCode": {"type": "Text", "value": "h"}},
                },
            ),
            (
                {
                    "name": "a_1",
                    "value": ["a", "b"],
                    "type": "Property",
                    "metadata": {"unitCode": {"type": "Text", "value": "h"}},
                },
                {
                    "name": "a_1",
                    "value": ["a", "b"],
                    "type": "Array",
                    "metadata": {"unitCode": {"type": "Text", "value": "h"}},
                },
            ),
            (
                {
                    "name": "a_1",
                    "value": {
                        "type": "Point",
                        "coordinates": [1.0, 2.0],
                    },
                    "type": "Property",
                    "metadata": {"unitCode": {"type": "Text", "value": "h"}},
                },
                {
                    "name": "a_1",
                    "value": {
                        "type": "Point",
                        "coordinates": [1.0, 2.0],
                    },
                    "type": "Object",
                    "metadata": {"unitCode": {"type": "Text", "value": "h"}},
                },
            ),
        ],
    )
    def test_static_attributes_translation_ld_to_v2(
        self, attrribute: Dict, expected_value: Dict
    ):
        """
        Test translation of static attributes from Ngsi-Ld to Ngsi-v2
        """
        assert ld_2_v2_static_attributes([attrribute])[0] == expected_value
