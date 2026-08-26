import pytest
from datetime import datetime
import xml.etree.ElementTree as ET

from jobs.data.data_importation.parser.kml_parser import KmlParser
from schemas.data_importation_request import DataImportationRequest
from schemas.entity_data_notification import EntityAttrType


@pytest.fixture
def parser():
    return KmlParser()


@pytest.fixture
def request_factory():
    def _factory(
        tenant="pid",
        scope="/",
        storage_file_path="test.kml",
    ):
        return DataImportationRequest(
            user_id=1,
            tenant=tenant,
            scope=scope,
            storage_file_path=storage_file_path,
        )
    return _factory


def write_kml(tmp_path, kml_content: str):
    file_path = tmp_path / "test.kml"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(kml_content)
    return str(file_path)


# ======================================================================
# BASIC PARSING
# ======================================================================
class TestKmlBasic:

    def test_single_placemark_basic_parsing(self, parser, request_factory, tmp_path):
        kml = """
        <kml xmlns="http://www.opengis.net/kml/2.2">
           <Placemark>
              <ExtendedData>
                 <Data name="entity_id"><value>urn:ngsi-ld:Device:001</value></Data>
                 <Data name="type"><value>Device</value></Data>
                 <Data name="timestamp"><value>2025-12-05T10:30:00Z</value></Data>
                 <Data name="temperature"><value>25.5</value></Data>
              </ExtendedData>
              <Point><coordinates>-3.0,42.0</coordinates></Point>
           </Placemark>
        </kml>
        """
        path = write_kml(tmp_path, kml)
        request = request_factory()

        notifications = parser.parse(path, request)

        assert len(notifications) == 1
        attrs = notifications[0].data
        assert len(attrs) == 2  # temperature + location
        assert any(a.name == "location" for a in attrs)


# ======================================================================
# TIMESTAMP HANDLING
# ======================================================================
class TestTimestampParsing:

    def test_fallback_timestamp_Timestamp_element(self, parser, request_factory, tmp_path):
        kml = """
        <kml xmlns="http://www.opengis.net/kml/2.2">
           <Placemark>
              <TimeStamp><when>2025-06-18T15:00:00</when></TimeStamp>
              <ExtendedData>
                 <Data name="entity_id"><value>urn:ngsi-ld:Device:002</value></Data>
                 <Data name="type"><value>Device</value></Data>
                 <Data name="value"><value>10</value></Data>
              </ExtendedData>
           </Placemark>
        </kml>
        """
        path = write_kml(tmp_path, kml)
        request = request_factory()

        notifications = parser.parse(path, request)
        ts = notifications[0].data[0].timestamp
        assert isinstance(ts, float)
        assert ts > 0


# ======================================================================
# VALUE TYPE PARSING
# ======================================================================
class TestValueParsing:

    @pytest.mark.parametrize("value,expected", [
        ("10", 10.0),
        ("-50.5", -50.5),
        ("true", True),
        ('{"a":1}', {"a": 1}),
        ("Hello", "Hello"),
    ])
    def test_value_parsing_extended_data(self, parser, request_factory, tmp_path, value, expected):

        kml = f"""
        <kml xmlns="http://www.opengis.net/kml/2.2">
           <Placemark>
              <ExtendedData>
                 <Data name="entity_id"><value>urn:ngsi-ld:Device:001</value></Data>
                 <Data name="type"><value>Device</value></Data>
                 <Data name="timestamp"><value>1750</value></Data>
                 <Data name="custom"><value>{value}</value></Data>
              </ExtendedData>
           </Placemark>
        </kml>
        """
        path = write_kml(tmp_path, kml)
        request = request_factory()

        notifications = parser.parse(path, request)
        v = notifications[0].data[0].value
        assert v == expected


# ======================================================================
# ENTITY MERGING
# ======================================================================
class TestEntityGrouping:

    def test_multiple_placemarks_same_entity(self, parser, request_factory, tmp_path):
        kml = """
        <kml xmlns="http://www.opengis.net/kml/2.2">
           <Placemark>
              <ExtendedData>
                 <Data name="entity_id"><value>urn:ngsi-ld:Dev:001</value></Data>
                 <Data name="type"><value>Dev</value></Data>
                 <Data name="timestamp"><value>1750</value></Data>
                 <Data name="temperature"><value>20</value></Data>
              </ExtendedData>
           </Placemark>
           <Placemark>
              <ExtendedData>
                 <Data name="entity_id"><value>urn:ngsi-ld:Dev:001</value></Data>
                 <Data name="type"><value>Dev</value></Data>
                 <Data name="timestamp"><value>1751</value></Data>
                 <Data name="humidity"><value>60</value></Data>
              </ExtendedData>
           </Placemark>
        </kml>
        """
        path = write_kml(tmp_path, kml)
        request = request_factory()

        notifications = parser.parse(path, request)

        assert len(notifications) == 1
        assert len(notifications[0].data) == 2


# ======================================================================
# ENTITY ID FROM FILE
# ======================================================================
class TestEntityIdFromFile:

    def test_entity_id_always_from_file(self, parser, request_factory, tmp_path):
        """Test that entity_id always comes from the file's ExtendedData."""
        kml = """
        <kml xmlns="http://www.opengis.net/kml/2.2">
           <Placemark>
              <ExtendedData>
                 <Data name="entity_id"><value>urn:ngsi-ld:Device:fromfile</value></Data>
                 <Data name="type"><value>Device</value></Data>
                 <Data name="timestamp"><value>1750</value></Data>
                 <Data name="value"><value>10</value></Data>
              </ExtendedData>
           </Placemark>
        </kml>
        """
        path = write_kml(tmp_path, kml)
        request = request_factory()

        notifications = parser.parse(path, request)

        assert len(notifications) == 1
        assert notifications[0].urn == "urn:ngsi-ld:Device:fromfile"


# ======================================================================
# ERROR / SKIPPING
# ======================================================================
class TestErrorCases:

    def test_missing_timestamp_placemark_skipped(self, parser, request_factory, tmp_path, caplog):
        kml = """
        <kml xmlns="http://www.opengis.net/kml/2.2">
           <Placemark>
              <ExtendedData>
                 <Data name="entity_id"><value>urn:ngsi-ld:Device:1</value></Data>
                 <Data name="temperature"><value>10</value></Data>
              </ExtendedData>
           </Placemark>
        </kml>
        """
        path = write_kml(tmp_path, kml)
        notifications = parser.parse(path, request_factory())

        assert len(notifications) == 0
        assert "timestamp" in caplog.text.lower()

    def test_missing_entity_id_skipped(self, parser, request_factory, tmp_path, caplog):
        kml = """
        <kml xmlns="http://www.opengis.net/kml/2.2">
           <Placemark>
              <ExtendedData>
                 <Data name="timestamp"><value>1750</value></Data>
                 <Data name="temp"><value>10</value></Data>
              </ExtendedData>
           </Placemark>
        </kml>
        """
        path = write_kml(tmp_path, kml)
        notifications = parser.parse(path, request_factory())

        assert len(notifications) == 0
        assert "entity_id" in caplog.text.lower()
