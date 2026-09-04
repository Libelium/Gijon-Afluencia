from typing import Any
from schemas.entity_data_notification import EntityAttrType
import utils.ngsi.ngsi_ld_utils as ngsi_ld_utils
import pytest


class TestNgsiLdUtils:

    @pytest.mark.parametrize(
        ("attr_key", "expected"),
        [
            ("id", True),
            ("type", True),
            ("@context", True),
            ("createdAt", True),
            ("modifiedAt", True),
            ("observedAt", True),
            ("deletedAt", True),
            ("temperature", False),
            ("controlledAsset", False),
            ("filling", False),
        ],
    )
    def test_is_system_attribute(self, attr_key: str, expected: bool):
        assert expected == ngsi_ld_utils.is_system_attribute(attr_key)

    @pytest.mark.parametrize(
        ("attr_key", "attr_value", "attr_type", "expected"),
        [
            (
                "command_info",
                {
                    "@type": "commandResult",
                    "@value": "SOME_VALUE",
                },
                "Property",
                True,
            ),
            (
                "command_status",
                {
                    "@type": "commandStatus",
                    "@value": "SOME_VALUE",
                },
                "Property",
                False,
            ),
            (
                "command_info",
                {
                    "@type": "commandResult",
                    "@value": "SOME_VALUE",
                },
                "Relationship",
                False,
            ),
            (
                "command_info",
                {
                    "@type": "commandStatus",
                    "@value": "SOME_VALUE",
                },
                "Property",
                False,
            ),
            (
                "not_command_info_key",
                {
                    "@type": "commandResult",
                    "@value": "SOME_VALUE",
                },
                "Property",
                False,
            ),
            ("command_info", "Nothing", "Property", False),
        ],
    )
    def test_is_command_info(
        self, attr_key: str, attr_value: str | dict, attr_type: str, expected: bool
    ):
        assert expected == ngsi_ld_utils.is_command_info(
            attr_key, attr_value, attr_type
        )

    @pytest.mark.parametrize(
        ("attr_key", "attr_value", "attr_type", "expected"),
        [
            (
                "command_status",
                {
                    "@type": "commandStatus",
                    "@value": "SOME_VALUE",
                },
                "Property",
                True,
            ),
            (
                "command_info",
                {
                    "@type": "commandResult",
                    "@value": "SOME_VALUE",
                },
                "Property",
                False,
            ),
            (
                "command_status",
                {
                    "@type": "commandStatus",
                    "@value": "SOME_VALUE",
                },
                "Relationship",
                False,
            ),
            (
                "command_status",
                {
                    "@type": "commandResult",
                    "@value": "SOME_VALUE",
                },
                "Property",
                False,
            ),
            (
                "not_command_status_key",
                {
                    "@type": "commandStatus",
                    "@value": "SOME_VALUE",
                },
                "Property",
                False,
            ),
            ("command_status", "Nothing", "Property", False),
        ],
    )
    def test_is_command_status(
        self, attr_key: str, attr_value: str | dict, attr_type: str, expected: bool
    ):
        assert expected == ngsi_ld_utils.is_command_status(
            attr_key, attr_value, attr_type
        )

    @pytest.mark.parametrize(
        ("attr_key", "expected"),
        [
            ("command_info", "command"),
            ("command_status", "command"),
            ("w_ota_info", "w_ota"),
            ("w_ota_status", "w_ota"),
            ("command_info_key", "command_info_key"),
            ("not_command_key", "not_command_key"),
        ],
    )
    def test_get_command_name(self, attr_key: str, expected: str):
        assert expected == ngsi_ld_utils.get_command_name(attr_key)

    @pytest.mark.parametrize(
        ("attr_value", "expected"),
        [
            (
                {
                    "observedAt": "2020-12-09T16:25:12.000Z",
                    "value": "urn:ngsi-ld:Building:farm001",
                    "type": "Property",
                },
                True,
            ),
            (
                {
                    "observedAt": "2020-12-09T16:25:12.000Z",
                    "object": "urn:ngsi-ld:Building:farm001",
                    "type": "Relationship",
                },
                True,
            ),
            (
                {
                    "observedAt": "2020-12-09T16:25:12.000Z",
                    "value": "urn:ngsi-ld:Building:farm001",
                    "type": "GeoProperty",
                },
                True,
            ),
            (
                {
                    "observedAt": "2020-12-09T16:25:12.000Z",
                    "value": "urn:ngsi-ld:Building:farm001",
                    "type": "Invalid",
                },
                False,
            ),
            (
                {
                    "value": "urn:ngsi-ld:Building:farm000",
                    "type": "Property",
                },
                False,
            ),
            (
                {
                    "ObservedAt": "2020-12-09T16:25:12.000Z",
                    "value": "urn:ngsi-ld:Building:farm001",
                    "type": "Property",
                },
                False,
            ),
        ],
    )
    def test_is_observed_attribute(self, attr_value: Any, expected: bool):
        assert ngsi_ld_utils.is_observed_attribute(attr_value) == expected

    @pytest.mark.parametrize(
        ("attr_value", "attr_type", "expected"),
        [
            (
                {
                    "value": "urn:ngsi-ld:Building:farm001",
                    "type": "Property",
                },
                "Property",
                True,
            ),
            (
                {
                    "object": "urn:ngsi-ld:Building:farm001",
                    "type": "Relationship",
                },
                "Relationship",
                True,
            ),
            (
                {
                    "value": "urn:ngsi-ld:Building:farm001",
                    "type": "GeoProperty",
                },
                "GeoProperty",
                True,
            ),
            (
                {
                    "value": "urn:ngsi-ld:Building:farm001",
                    "type": "Invalid",
                },
                "Invalid",
                False,
            ),
            (
                {
                    "value": "urn:ngsi-ld:Building:farm001",
                    "type": "Relationship",
                },
                "Relationship",
                False,
            ),
        ],
    )
    def test_has_value(self, attr_value: Any, attr_type: str, expected: bool):
        assert ngsi_ld_utils.has_value(attr_value, attr_type) == expected

    @pytest.mark.parametrize(
        ("attr_value", "expected"),
        [
            (None, False),
            (
                {
                    "@value": None,
                },
                True,
            ),
            (
                "urn:ngsi-ld:Building:farm001",
                False,
            ),
            (
                {
                    "value": "urn:ngsi-ld:Building:farm001",
                    "type": "Property",
                },
                False,
            ),
        ],
    )
    def test_is_jsonld_null(self, attr_value: Any, expected: bool):
        assert ngsi_ld_utils.is_jsonld_null(attr_value) == expected

    @pytest.mark.parametrize(
        ("attr_value", "attr_type", "expected_type", "expected_measure"),
        [
            (
                {
                    "value": 0.25,
                    "type": "Property",
                },
                "Property",
                EntityAttrType.PROPERTY,
                0.25,
            ),
            (
                {
                    "value": "urn:ngsi-ld:Building:farm001",
                    "type": "Property",
                },
                "Property",
                EntityAttrType.PROPERTY,
                "urn:ngsi-ld:Building:farm001",
            ),
            (
                {
                    "object": "urn:ngsi-ld:Building:farm001",
                    "type": "Relationship",
                },
                "Relationship",
                EntityAttrType.RELATIONSHIP,
                "urn:ngsi-ld:Building:farm001",
            ),
            (
                {
                    "value": 0.25,
                    "type": "GeoProperty",
                },
                "GeoProperty",
                EntityAttrType.PROPERTY,
                0.25,
            ),
            (
                {
                    "value": 0.25,
                    "type": "Invalid",
                },
                "Invalid",
                EntityAttrType.PROPERTY,
                0.25,
            ),
            (
                {
                    "object": "urn:ngsi-ld:Building:farm001",
                    "type": "Invalid",
                },
                "Invalid",
                EntityAttrType.PROPERTY,
                None,
            ),
            (
                {
                    "value": "urn:ngsi-ld:Building:farm001",
                    "type": "Relationship",
                },
                "Relationship",
                EntityAttrType.RELATIONSHIP,
                None,
            ),
            (
                {
                    "value": {
                        "@value": None,
                    },
                    "type": "Property",
                },
                "Property",
                EntityAttrType.PROPERTY,
                None,
            ),
        ],
    )
    def test_get_attr_value_and_type(
        self,
        attr_value: Any,
        attr_type: str,
        expected_type: EntityAttrType,
        expected_measure: Any,
    ):
        measure_value, measure_type = ngsi_ld_utils.get_attr_value_and_type(
            attr_value, attr_type
        )
        assert expected_measure == measure_value
        assert expected_type == measure_type
