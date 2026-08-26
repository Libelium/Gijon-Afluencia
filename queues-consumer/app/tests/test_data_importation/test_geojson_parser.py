import json
import pytest
import tempfile
from datetime import datetime
from jobs.data.data_importation.parser.geojson_parser import GeoJsonParser
from schemas.data_importation_request import DataImportationRequest
from schemas.entity_data_notification import EntityAttrType


@pytest.fixture
def parser():
    return GeoJsonParser()


@pytest.fixture
def request_factory():
    def _factory(
        tenant="tenant1", scope="/", path="test.geojson"
    ):
        return DataImportationRequest(
            user_id=1,
            tenant=tenant,
            scope=scope,
            storage_file_path=path,
        )
    return _factory


def write_geojson(tmp_path, geojson_obj):
    file_path = tmp_path / "data.geojson"
    with open(file_path, "w") as f:
        json.dump(geojson_obj, f)
    return str(file_path)


class TestGeoJsonBasicParsing:

    def test_valid_feature_collection(self, parser, request_factory, tmp_path):
        geo = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "entity_id": "urn:ngsi-ld:Device:001",
                        "type": "Device",
                        "timestamp": "1750258530",
                        "temperature": 25.5,
                    },
                    "geometry": {"type": "Point", "coordinates": [1, 2]},
                }
            ],
        }
        path = write_geojson(tmp_path, geo)
        request = request_factory()

        notifications = parser.parse(path, request)

        assert len(notifications) == 1
        notif = notifications[0]
        assert notif.urn == "urn:ngsi-ld:Device:001"
        assert len(notif.data) == 2  # temperature + location


class TestTimestampParsing:

    def test_iso_timestamp(self, parser, request_factory, tmp_path):
        ts_iso = "2025-06-18T14:55:30Z"
        geo = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "entity_id": "urn:ngsi-ld:Device:002",
                        "type": "Device",
                        "timestamp": ts_iso,
                        "value": "10",
                    }
                }
            ],
        }
        path = write_geojson(tmp_path, geo)
        request = request_factory()

        notifications = parser.parse(path, request)
        ts = notifications[0].data[0].timestamp
        assert isinstance(ts, float)
        assert ts > 0


class TestGeometry:

    def test_geometry_included_as_location(self, parser, request_factory, tmp_path):
        geo = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "entity_id": "urn:ngsi-ld:Device:001",
                        "type": "Device",
                        "timestamp": 1750,
                        "speed": 50,
                    },
                    "geometry": {"type": "Point", "coordinates": [-3.0, 42.0]},
                }
            ],
        }
        path = write_geojson(tmp_path, geo)
        request = request_factory()

        notifications = parser.parse(path, request)
        attrs = notifications[0].data

        loc = next(a for a in attrs if a.name == "location")
        assert loc.type == EntityAttrType.PROPERTY
        assert loc.value["type"] == "Point"


class TestInvalidFeatures:

    def test_invalid_urn_skipped(self, parser, request_factory, tmp_path, caplog):
        geo = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "entity_id": "INVALID",
                        "timestamp": 1750,
                        "temperature": 20
                    }
                }
            ],
        }
        path = write_geojson(tmp_path, geo)
        request = request_factory()

        notifications = parser.parse(path, request)

        assert len(notifications) == 0
        assert "invalid NGSI-LD URN" in caplog.text


class TestMultipleFeatures:

    def test_each_feature_keeps_its_own_urn(self, parser, request_factory, tmp_path):
        """Test that each feature uses its own entity_id from the file."""
        geo = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "entity_id": "urn:ngsi-ld:Device:001",
                        "type": "Device",
                        "timestamp": 1750,
                        "value": 10
                    }
                },
                {
                    "type": "Feature",
                    "properties": {
                        "entity_id": "urn:ngsi-ld:Device:002",
                        "type": "Device",
                        "timestamp": 1751,
                        "value": 20
                    }
                }
            ],
        }

        path = write_geojson(tmp_path, geo)
        request = request_factory()

        notifications = parser.parse(path, request)

        assert len(notifications) == 2
        urns = {n.urn for n in notifications}
        assert urns == {"urn:ngsi-ld:Device:001", "urn:ngsi-ld:Device:002"}


class TestErrorConditions:

    def test_not_feature_collection(self, parser, request_factory, tmp_path):
        path = write_geojson(tmp_path, {"type": "Invalid"})
        request = request_factory()

        with pytest.raises(ValueError, match="FeatureCollection"):
            parser.parse(path, request)

    def test_empty_features(self, parser, request_factory, tmp_path):
        path = write_geojson(tmp_path, {"type": "FeatureCollection", "features": []})
        request = request_factory()

        with pytest.raises(ValueError, match="no features"):
            parser.parse(path, request)
