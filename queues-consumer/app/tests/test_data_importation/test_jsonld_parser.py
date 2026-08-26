import json
import pytest
import tempfile
from datetime import datetime
from jobs.data.data_importation.parser.jsonld_parser import JsonLdParser
from schemas.data_importation_request import DataImportationRequest
from schemas.entity_data_notification import EntityAttrType


@pytest.fixture
def parser():
    return JsonLdParser()


@pytest.fixture
def request_factory():
    def _factory(
        tenant="tenant1", scope="/", path="test.jsonld"
    ):
        return DataImportationRequest(
            user_id=1,
            tenant=tenant,
            scope=scope,
            storage_file_path=path,
        )
    return _factory


def write_jsonld(tmp_path, data):
    file_path = tmp_path / "data.jsonld"
    with open(file_path, "w") as f:
        json.dump(data, f)
    return str(file_path)


class TestJsonLdBasicParsing:

    def test_single_entity_in_array(self, parser, request_factory, tmp_path):
        data = [
            {
                "id": "urn:ngsi-ld:Device:001",
                "type": "Device",
                "temperature": {
                    "type": "Property",
                    "value": 25.5,
                    "observedAt": "2025-06-18T14:55:30Z",
                },
            }
        ]
        path = write_jsonld(tmp_path, data)
        request = request_factory()

        notifications = parser.parse(path, request)

        assert len(notifications) == 1
        notif = notifications[0]
        assert notif.urn == "urn:ngsi-ld:Device:001"
        assert notif.type == "Device"
        assert notif.tenant == "tenant1"
        assert notif.scope == "/"
        assert len(notif.data) == 1
        assert notif.data[0].name == "temperature"
        assert notif.data[0].value == 25.5

    def test_single_entity_object(self, parser, request_factory, tmp_path):
        data = {
            "id": "urn:ngsi-ld:Device:002",
            "type": "Device",
            "humidity": {
                "type": "Property",
                "value": 60.0,
            },
        }
        path = write_jsonld(tmp_path, data)
        request = request_factory()

        notifications = parser.parse(path, request)

        assert len(notifications) == 1
        assert notifications[0].urn == "urn:ngsi-ld:Device:002"

    def test_multiple_entities(self, parser, request_factory, tmp_path):
        data = [
            {
                "id": "urn:ngsi-ld:Device:001",
                "type": "Device",
                "temperature": {"type": "Property", "value": 20.0},
            },
            {
                "id": "urn:ngsi-ld:Device:002",
                "type": "Device",
                "temperature": {"type": "Property", "value": 30.0},
            },
        ]
        path = write_jsonld(tmp_path, data)
        request = request_factory()

        notifications = parser.parse(path, request)

        assert len(notifications) == 2
        urns = {n.urn for n in notifications}
        assert urns == {"urn:ngsi-ld:Device:001", "urn:ngsi-ld:Device:002"}


class TestAttributeTypes:

    def test_property_attribute(self, parser, request_factory, tmp_path):
        data = [
            {
                "id": "urn:ngsi-ld:Device:001",
                "type": "Device",
                "temperature": {
                    "type": "Property",
                    "value": 25.5,
                    "observedAt": "2025-06-18T14:55:30Z",
                },
            }
        ]
        path = write_jsonld(tmp_path, data)
        request = request_factory()

        notifications = parser.parse(path, request)
        attr = notifications[0].data[0]

        assert attr.name == "temperature"
        assert attr.value == 25.5
        assert attr.type == EntityAttrType.PROPERTY

    def test_relationship_attribute(self, parser, request_factory, tmp_path):
        data = [
            {
                "id": "urn:ngsi-ld:Device:001",
                "type": "Device",
                "refOwner": {
                    "type": "Relationship",
                    "object": "urn:ngsi-ld:Person:owner-001",
                },
            }
        ]
        path = write_jsonld(tmp_path, data)
        request = request_factory()

        notifications = parser.parse(path, request)
        attr = notifications[0].data[0]

        assert attr.name == "refOwner"
        assert attr.type == EntityAttrType.RELATIONSHIP

    def test_geoproperty_attribute(self, parser, request_factory, tmp_path):
        data = [
            {
                "id": "urn:ngsi-ld:Device:001",
                "type": "Device",
                "location": {
                    "type": "GeoProperty",
                    "value": {
                        "type": "Point",
                        "coordinates": [-3.7038, 40.4168],
                    },
                },
            }
        ]
        path = write_jsonld(tmp_path, data)
        request = request_factory()

        notifications = parser.parse(path, request)
        attr = notifications[0].data[0]

        assert attr.name == "location"
        assert attr.type == EntityAttrType.PROPERTY
        assert attr.value["type"] == "Point"
        assert attr.value["coordinates"] == [-3.7038, 40.4168]

    def test_observed_at_timestamp(self, parser, request_factory, tmp_path):
        data = [
            {
                "id": "urn:ngsi-ld:Device:001",
                "type": "Device",
                "temperature": {
                    "type": "Property",
                    "value": 25.5,
                    "observedAt": "2025-06-18T14:55:30Z",
                },
            }
        ]
        path = write_jsonld(tmp_path, data)
        request = request_factory()

        notifications = parser.parse(path, request)
        attr = notifications[0].data[0]

        assert isinstance(attr.timestamp, float)
        assert attr.timestamp > 0
        assert attr.timestamp_override is False

    def test_missing_observed_at_uses_default(self, parser, request_factory, tmp_path):
        data = [
            {
                "id": "urn:ngsi-ld:Device:001",
                "type": "Device",
                "temperature": {
                    "type": "Property",
                    "value": 25.5,
                },
            }
        ]
        path = write_jsonld(tmp_path, data)
        request = request_factory()

        notifications = parser.parse(path, request)
        attr = notifications[0].data[0]

        assert isinstance(attr.timestamp, float)
        assert attr.timestamp_override is True

    def test_unit_code(self, parser, request_factory, tmp_path):
        data = [
            {
                "id": "urn:ngsi-ld:Device:001",
                "type": "Device",
                "temperature": {
                    "type": "Property",
                    "value": 25.5,
                    "unitCode": "CEL",
                    "observedAt": "2025-06-18T14:55:30Z",
                },
            }
        ]
        path = write_jsonld(tmp_path, data)
        request = request_factory()

        notifications = parser.parse(path, request)
        attr = notifications[0].data[0]

        assert attr.units == "CEL"


class TestTenantScopeFromRequest:

    def test_tenant_scope_from_request(self, parser, request_factory, tmp_path):
        data = [
            {
                "id": "urn:ngsi-ld:Device:001",
                "type": "Device",
                "temperature": {"type": "Property", "value": 20.0},
            }
        ]
        path = write_jsonld(tmp_path, data)
        request = request_factory(tenant="my_tenant", scope="/my/scope")

        notifications = parser.parse(path, request)

        assert notifications[0].tenant == "my_tenant"
        assert notifications[0].scope == "/my/scope"

    def test_missing_tenant_scope_raises_error(self, parser, request_factory, tmp_path):
        data = [
            {
                "id": "urn:ngsi-ld:Device:001",
                "type": "Device",
                "temperature": {"type": "Property", "value": 20.0},
            }
        ]
        path = write_jsonld(tmp_path, data)
        request = request_factory(tenant=None, scope=None)

        with pytest.raises(ValueError):
            parser.parse(path, request)


class TestInvalidEntities:

    def test_invalid_urn_skipped(self, parser, request_factory, tmp_path, caplog):
        data = [
            {
                "id": "INVALID",
                "type": "Device",
                "temperature": {"type": "Property", "value": 20.0},
            }
        ]
        path = write_jsonld(tmp_path, data)
        request = request_factory()

        notifications = parser.parse(path, request)

        assert len(notifications) == 0
        assert "invalid or missing URN" in caplog.text

    def test_missing_id_skipped(self, parser, request_factory, tmp_path, caplog):
        data = [
            {
                "type": "Device",
                "temperature": {"type": "Property", "value": 20.0},
            }
        ]
        path = write_jsonld(tmp_path, data)
        request = request_factory()

        notifications = parser.parse(path, request)

        assert len(notifications) == 0
        assert "invalid or missing URN" in caplog.text

    def test_missing_type_skipped(self, parser, request_factory, tmp_path):
        data = [
            {
                "id": "urn:ngsi-ld:Device:001",
                "temperature": {"type": "Property", "value": 20.0},
            }
        ]
        path = write_jsonld(tmp_path, data)
        request = request_factory()

        notifications = parser.parse(path, request)

        assert len(notifications) == 0

    def test_non_object_entry_skipped(self, parser, request_factory, tmp_path, caplog):
        data = [
            "not an object",
            {
                "id": "urn:ngsi-ld:Device:001",
                "type": "Device",
                "temperature": {"type": "Property", "value": 20.0},
            },
        ]
        path = write_jsonld(tmp_path, data)
        request = request_factory()

        notifications = parser.parse(path, request)

        assert len(notifications) == 1
        assert "non-object" in caplog.text

    def test_valid_and_invalid_mixed(self, parser, request_factory, tmp_path):
        data = [
            {
                "id": "INVALID-URN",
                "type": "Device",
                "temperature": {"type": "Property", "value": 10.0},
            },
            {
                "id": "urn:ngsi-ld:Device:001",
                "type": "Device",
                "temperature": {"type": "Property", "value": 20.0},
            },
        ]
        path = write_jsonld(tmp_path, data)
        request = request_factory()

        notifications = parser.parse(path, request)

        assert len(notifications) == 1
        assert notifications[0].urn == "urn:ngsi-ld:Device:001"


class TestErrorConditions:

    def test_empty_array(self, parser, request_factory, tmp_path):
        path = write_jsonld(tmp_path, [])
        request = request_factory()

        with pytest.raises(ValueError, match="no entities"):
            parser.parse(path, request)

    def test_invalid_json(self, parser, request_factory, tmp_path):
        file_path = tmp_path / "bad.jsonld"
        with open(file_path, "w") as f:
            f.write("not json {{{")
        request = request_factory()

        with pytest.raises(Exception):
            parser.parse(str(file_path), request)

    def test_non_object_non_array(self, parser, request_factory, tmp_path):
        path = write_jsonld(tmp_path, "just a string")
        request = request_factory()

        with pytest.raises(ValueError, match="object or an array"):
            parser.parse(path, request)


class TestSystemAttributesIgnored:

    def test_context_and_system_attrs_excluded(self, parser, request_factory, tmp_path):
        data = [
            {
                "id": "urn:ngsi-ld:Device:001",
                "type": "Device",
                "@context": "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld",
                "createdAt": "2025-01-01T00:00:00Z",
                "modifiedAt": "2025-01-02T00:00:00Z",
                "temperature": {
                    "type": "Property",
                    "value": 25.5,
                    "observedAt": "2025-06-18T14:55:30Z",
                },
            }
        ]
        path = write_jsonld(tmp_path, data)
        request = request_factory()

        notifications = parser.parse(path, request)

        attr_names = [a.name for a in notifications[0].data]
        assert "temperature" in attr_names
        assert "@context" not in attr_names
        assert "createdAt" not in attr_names
        assert "modifiedAt" not in attr_names


class TestFileExtension:

    def test_get_file_extension(self, parser):
        assert parser.get_file_extension() == "jsonld"
