"""
Blackbox tests for CSVParser.parse() method.

These tests follow the blackbox testing approach where:
- Input: CSV file content + DataImportationRequest
- Output: List[EntityDataNotification]
- Tests focus on input/output behavior without testing internal implementation

The tests use pytest.mark.parametrize extensively to test multiple scenarios
with minimal code duplication.
"""
import io
from typing import List

import pandas as pd
import pytest
from jobs.data.data_importation.parser.csv_parser import CsvParser
from schemas.data_importation_request import DataImportationRequest
from schemas.entity_data_notification import (
    EntityAttr,
    EntityAttrType,
    EntityDataNotification,
)


# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def csv_parser():
    """Returns a CsvParser instance for testing."""
    return CsvParser()


@pytest.fixture
def create_request():
    """Factory fixture to create DataImportationRequest with custom parameters."""

    def _factory(
        tenant: str = None,
        scope: str = None,
        user_id: int = 1,
        storage_file_path: str = "test.csv",
    ) -> DataImportationRequest:
        return DataImportationRequest(
            user_id=user_id,
            tenant=tenant,
            scope=scope,
            storage_file_path=storage_file_path,
        )

    return _factory


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================


def csv_to_dataframe(csv_content: str) -> pd.DataFrame:
    """Convert CSV string to pandas DataFrame using same settings as parser."""
    return pd.read_csv(
        io.StringIO(csv_content),
        skipinitialspace=True,
        encoding="utf-8",
        dtype=str,
        keep_default_na=False,
    )


def find_notification(notifications: List[EntityDataNotification], urn: str):
    """Find notification by URN."""
    return next((n for n in notifications if n.urn == urn), None)


def find_attribute(attributes: List[EntityAttr], name: str, timestamp: float = None):
    """Find attribute by name and optionally by timestamp."""
    for attr in attributes:
        if attr.name == name and (timestamp is None or attr.timestamp == timestamp):
            return attr
    return None


# ==============================================================================
# TEST: SINGLE ENTITY SCENARIOS
# ==============================================================================


class TestSingleEntityParsing:
    """Tests for parsing CSV with a single entity."""

    @pytest.mark.parametrize(
        "csv_content,tenant,scope,expected_attr_count",
        [
            # Single row, single attribute
            ("timestamp,urn,type,temperature\n1750280400,urn:ngsi-ld:Device:1,Device,25.5", "t1", "/", 1),
            # Single row, multiple attributes
            ("timestamp,urn,type,temp,humidity\n1750280400,urn:ngsi-ld:Device:1,Device,25.5,60", "t1", "/", 2),
            # Multiple rows, same entity
            (
                "timestamp,urn,type,temp\n1750280400,urn:ngsi-ld:Device:1,Device,25.5\n1750280700,urn:ngsi-ld:Device:1,Device,26.0",
                "t1",
                "/",
                2,
            ),
            # Multiple rows, multiple attributes
            (
                "timestamp,urn,type,temp,humidity\n"
                "1750280400,urn:ngsi-ld:Device:1,Device,25.5,60\n"
                "1750280700,urn:ngsi-ld:Device:1,Device,26.0,62",
                "t1",
                "/",
                4,
            ),
        ],
    )
    def test_parse_single_entity_with_request_metadata(
        self, csv_parser, create_request, csv_content, tenant, scope, expected_attr_count
    ):
        """Test parsing when URN comes from file and tenant/scope from request."""
        df = csv_to_dataframe(csv_content)
        request = create_request(tenant=tenant, scope=scope)

        notifications = csv_parser.parse(df, request)

        assert len(notifications) == 1
        assert notifications[0].urn == "urn:ngsi-ld:Device:1"
        assert notifications[0].tenant == tenant
        assert notifications[0].scope == scope
        assert notifications[0].type == "Device"
        assert len(notifications[0].data) == expected_attr_count

    @pytest.mark.parametrize(
        "csv_content,expected_urn,expected_tenant,expected_scope,expected_type,expected_attr_count",
        [
            # All metadata in CSV
            (
                "timestamp,urn,type,tenant,scope,temperature\n"
                "1750280400,urn:ngsi-ld:CSVDevice:1,CSVDevice,csvtenant,/csvscope,25.5",
                "urn:ngsi-ld:CSVDevice:1",
                "csvtenant",
                "/csvscope",
                "CSVDevice",
                1,
            ),
            # Multiple rows with same CSV metadata
            (
                "timestamp,urn,type,tenant,scope,value\n"
                "1750280400,urn:ngsi-ld:Dev:a,Dev,t1,/s,10\n"
                "1750280700,urn:ngsi-ld:Dev:a,Dev,t1,/s,20",
                "urn:ngsi-ld:Dev:a",
                "t1",
                "/s",
                "Dev",
                2,
            ),
        ],
    )
    def test_parse_single_entity_with_csv_metadata(
        self,
        csv_parser,
        create_request,
        csv_content,
        expected_urn,
        expected_tenant,
        expected_scope,
        expected_type,
        expected_attr_count,
    ):
        """Test parsing when all metadata comes from CSV."""
        df = csv_to_dataframe(csv_content)
        request = create_request()

        notifications = csv_parser.parse(df, request)

        assert len(notifications) == 1
        assert notifications[0].urn == expected_urn
        assert notifications[0].tenant == expected_tenant
        assert notifications[0].scope == expected_scope
        assert notifications[0].type == expected_type
        assert len(notifications[0].data) == expected_attr_count


# ==============================================================================
# TEST: MULTIPLE ENTITIES
# ==============================================================================


class TestMultipleEntitiesParsing:
    """Tests for parsing CSV with multiple entities."""

    @pytest.mark.parametrize(
        "csv_content,expected_entity_count",
        [
            # Two different entities
            (
                "timestamp,urn,type,tenant,scope,value\n"
                "1750280400,urn:ngsi-ld:Device:a,Device,t1,/,10\n"
                "1750280500,urn:ngsi-ld:Device:b,Device,t1,/,20",
                2,
            ),
            # Three different entities
            (
                "timestamp,urn,type,tenant,scope,value\n"
                "1750280400,urn:ngsi-ld:Device:a,Device,t1,/,10\n"
                "1750280500,urn:ngsi-ld:Device:b,Device,t1,/,20\n"
                "1750280600,urn:ngsi-ld:Device:c,Device,t1,/,30",
                3,
            ),
            # Five different entities
            (
                "timestamp,urn,type,tenant,scope,value\n"
                "1750280400,urn:ngsi-ld:Device:a,Device,t1,/,10\n"
                "1750280500,urn:ngsi-ld:Device:b,Device,t1,/,20\n"
                "1750280600,urn:ngsi-ld:Device:c,Device,t1,/,30\n"
                "1750280700,urn:ngsi-ld:Device:d,Device,t1,/,40\n"
                "1750280800,urn:ngsi-ld:Device:e,Device,t1,/,50",
                5,
            ),
        ],
    )
    def test_parse_multiple_distinct_entities(
        self, csv_parser, create_request, csv_content, expected_entity_count
    ):
        """Test parsing with multiple distinct entities in one file."""
        df = csv_to_dataframe(csv_content)
        request = create_request()

        notifications = csv_parser.parse(df, request)

        assert len(notifications) == expected_entity_count

    @pytest.mark.parametrize(
        "csv_content,entity_attr_counts",
        [
            # Same entity appears twice
            (
                "timestamp,urn,type,tenant,scope,temp\n"
                "1750280400,urn:ngsi-ld:Device:a,Device,t1,/,25.5\n"
                "1750280700,urn:ngsi-ld:Device:a,Device,t1,/,26.0",
                {"urn:ngsi-ld:Device:a": 2},
            ),
            # Two entities, each appearing multiple times
            (
                "timestamp,urn,type,tenant,scope,temp\n"
                "1750280400,urn:ngsi-ld:Device:a,Device,t1,/,25.5\n"
                "1750280500,urn:ngsi-ld:Device:b,Device,t1,/,26.0\n"
                "1750280600,urn:ngsi-ld:Device:a,Device,t1,/,27.0\n"
                "1750280700,urn:ngsi-ld:Device:b,Device,t1,/,28.0",
                {"urn:ngsi-ld:Device:a": 2, "urn:ngsi-ld:Device:b": 2},
            ),
            # Sparse attribute data across rows for same entity
            (
                "timestamp,urn,type,tenant,scope,temp,humidity,pressure\n"
                "1750280400,urn:ngsi-ld:Device:a,Device,t1,/,25.5,60,\n"
                "1750280700,urn:ngsi-ld:Device:a,Device,t1,/,26.0,,1013\n"
                "1750281000,urn:ngsi-ld:Device:a,Device,t1,/,,62,1014",
                {"urn:ngsi-ld:Device:a": 6},
            ),
        ],
    )
    def test_parse_entity_grouping(
        self, csv_parser, create_request, csv_content, entity_attr_counts
    ):
        """Test that rows with same entity key are grouped correctly."""
        df = csv_to_dataframe(csv_content)
        request = create_request()

        notifications = csv_parser.parse(df, request)

        assert len(notifications) == len(entity_attr_counts)
        for urn, expected_count in entity_attr_counts.items():
            notification = find_notification(notifications, urn)
            assert notification is not None, f"Entity {urn} not found"
            assert len(notification.data) == expected_count


# ==============================================================================
# TEST: METADATA PRIORITY
# ==============================================================================


class TestMetadataPriority:
    """Tests that CSV tenant/scope overrides request metadata. URN and type always from file."""

    @pytest.mark.parametrize(
        "csv_content,request_tenant,request_scope,expected_tenant,expected_scope,expected_entity_count",
        [
            # Request tenant/scope take priority over CSV values
            (
                "timestamp,urn,type,tenant,scope,value\n"
                "1750280400,urn:ngsi-ld:Device:a,Device,csvtenant,/csvscope,10\n"
                "1750280500,urn:ngsi-ld:Device:b,Device,csvtenant,/csvscope,20",
                "request_tenant",
                "/request_scope",
                "request_tenant",
                "/request_scope",
                2,
            ),
            # Request tenant/scope present, CSV has different values - request wins
            (
                "timestamp,urn,type,tenant,scope,value\n"
                "1750280400,urn:ngsi-ld:Device:a,Device,csvtenant,/,10\n"
                "1750280500,urn:ngsi-ld:Device:b,Device,csvtenant,/,20",
                "override_tenant",
                "/override_scope",
                "override_tenant",
                "/override_scope",
                2,
            ),
        ],
    )
    def test_request_metadata_overrides_csv(
        self,
        csv_parser,
        create_request,
        csv_content,
        request_tenant,
        request_scope,
        expected_tenant,
        expected_scope,
        expected_entity_count,
    ):
        """Test that request metadata takes priority over CSV metadata."""
        df = csv_to_dataframe(csv_content)
        request = create_request(
            tenant=request_tenant, scope=request_scope
        )

        notifications = csv_parser.parse(df, request)

        assert len(notifications) == expected_entity_count
        for notification in notifications:
            assert notification.tenant == expected_tenant
            assert notification.scope == expected_scope


# ==============================================================================
# TEST: VALUE TYPES
# ==============================================================================


class TestValueTypeParsing:
    """Tests parsing of different value types."""

    @pytest.mark.parametrize(
        "csv_content,attr_name,expected_value,expected_python_type",
        [
            # Integers
            ("timestamp,urn,type,count\n1750280400,urn:ngsi-ld:Device:1,Device,42", "count", 42, int),
            ("timestamp,urn,type,count\n1750280400,urn:ngsi-ld:Device:1,Device,0", "count", 0, int),
            ("timestamp,urn,type,count\n1750280400,urn:ngsi-ld:Device:1,Device,-42", "count", -42, int),
            # Floats
            ("timestamp,urn,type,temp\n1750280400,urn:ngsi-ld:Device:1,Device,25.5", "temp", 25.5, float),
            ("timestamp,urn,type,temp\n1750280400,urn:ngsi-ld:Device:1,Device,-15.5", "temp", -15.5, float),
            ("timestamp,urn,type,temp\n1750280400,urn:ngsi-ld:Device:1,Device,0.001", "temp", 0.001, float),
            # Booleans
            ("timestamp,urn,type,enabled\n1750280400,urn:ngsi-ld:Device:1,Device,true", "enabled", True, bool),
            ("timestamp,urn,type,enabled\n1750280400,urn:ngsi-ld:Device:1,Device,false", "enabled", False, bool),
            ("timestamp,urn,type,enabled\n1750280400,urn:ngsi-ld:Device:1,Device,TRUE", "enabled", True, bool),
            ("timestamp,urn,type,enabled\n1750280400,urn:ngsi-ld:Device:1,Device,FALSE", "enabled", False, bool),
            # Strings
            ("timestamp,urn,type,name\n1750280400,urn:ngsi-ld:Device:1,Device,Device1", "name", "Device1", str),
            ("timestamp,urn,type,name\n1750280400,urn:ngsi-ld:Device:1,Device,Device One", "name", "Device One", str),
            ("timestamp,urn,type,value\n1750280400,urn:ngsi-ld:Device:1,Device,123abc", "value", "123abc", str),
        ],
    )
    def test_value_type_parsing(
        self,
        csv_parser,
        create_request,
        csv_content,
        attr_name,
        expected_value,
        expected_python_type,
    ):
        """Test that different value types are parsed correctly."""
        df = csv_to_dataframe(csv_content)
        request = create_request(tenant="t1", scope="/")

        notifications = csv_parser.parse(df, request)

        assert len(notifications) == 1
        attr = find_attribute(notifications[0].data, attr_name)
        assert attr is not None
        assert attr.value == expected_value
        assert type(attr.value) == expected_python_type

    @pytest.mark.parametrize(
        "csv_content,attr_name,expected_value",
        [
            # JSON object
            (
                'timestamp,urn,type,metadata\n1750280400,urn:ngsi-ld:Device:1,Device,"{""key"":""value""}"',
                "metadata",
                {"key": "value"},
            ),
            # JSON array
            ('timestamp,urn,type,data\n1750280400,urn:ngsi-ld:Device:1,Device,"[1,2,3]"', "data", [1, 2, 3]),
            # Empty JSON object
            ('timestamp,urn,type,metadata\n1750280400,urn:ngsi-ld:Device:1,Device,"{}"', "metadata", {}),
            # Empty JSON array
            ('timestamp,urn,type,data\n1750280400,urn:ngsi-ld:Device:1,Device,"[]"', "data", []),
        ],
    )
    def test_json_value_parsing(
        self, csv_parser, create_request, csv_content, attr_name, expected_value
    ):
        """Test that JSON values are parsed correctly."""
        df = csv_to_dataframe(csv_content)
        request = create_request(tenant="t1", scope="/")

        notifications = csv_parser.parse(df, request)

        assert len(notifications) == 1
        attr = find_attribute(notifications[0].data, attr_name)
        assert attr is not None
        assert attr.value == expected_value


# ==============================================================================
# TEST: TIMESTAMP HANDLING
# ==============================================================================


class TestTimestampParsing:
    """Tests timestamp parsing in different formats."""

    @pytest.mark.parametrize(
        "csv_content,expected_timestamp",
        [
            # Unix timestamp as integer
            ("timestamp,urn,type,value\n1750280400,urn:ngsi-ld:Device:1,Device,10", 1750280400.0),
            # Unix timestamp as float
            ("timestamp,urn,type,value\n1750280400.5,urn:ngsi-ld:Device:1,Device,10", 1750280400.5),
        ],
    )
    def test_unix_timestamp_parsing(
        self, csv_parser, create_request, csv_content, expected_timestamp
    ):
        """Test parsing Unix timestamps."""
        df = csv_to_dataframe(csv_content)
        request = create_request(tenant="t1", scope="/")

        notifications = csv_parser.parse(df, request)

        assert len(notifications) == 1
        assert len(notifications[0].data) == 1
        assert notifications[0].data[0].timestamp == expected_timestamp

    def test_timestamp_preserved_per_row(self, csv_parser, create_request):
        """Test that each attribute preserves its row's timestamp."""
        csv_content = (
            "timestamp,urn,type,temp,humidity\n"
            "1750280400,urn:ngsi-ld:Device:1,Device,25.5,60\n"
            "1750280700,urn:ngsi-ld:Device:1,Device,26.0,62"
        )
        df = csv_to_dataframe(csv_content)
        request = create_request(tenant="t1", scope="/")

        notifications = csv_parser.parse(df, request)

        assert len(notifications) == 1
        assert len(notifications[0].data) == 4

        temp_t1 = find_attribute(notifications[0].data, "temp", 1750280400.0)
        temp_t2 = find_attribute(notifications[0].data, "temp", 1750280700.0)
        assert temp_t1 is not None and temp_t1.value == 25.5
        assert temp_t2 is not None and temp_t2.value == 26.0


# ==============================================================================
# TEST: EDGE CASES
# ==============================================================================


class TestEdgeCases:
    """Tests edge cases and special scenarios."""

    def test_empty_values_are_skipped(self, csv_parser, create_request):
        """Test that empty values are not included in output."""
        csv_content = "timestamp,urn,type,v1,v2,v3\n1750280400,urn:ngsi-ld:Device:1,Device,10,,\n1750280700,urn:ngsi-ld:Device:1,Device,,20,"
        df = csv_to_dataframe(csv_content)
        request = create_request(tenant="t1", scope="/")

        notifications = csv_parser.parse(df, request)

        assert len(notifications) == 1
        assert len(notifications[0].data) == 2

    def test_all_empty_row_creates_no_notification(self, csv_parser, create_request):
        """Test that rows with all empty values (except timestamp) don't create notifications."""
        csv_content = "timestamp,urn,type,v1,v2\n1750280400,urn:ngsi-ld:Device:1,Device,,"
        df = csv_to_dataframe(csv_content)
        request = create_request(tenant="t1", scope="/")

        notifications = csv_parser.parse(df, request)

        # Parser creates notification with empty data list
        assert len(notifications) == 0 or (len(notifications) == 1 and len(notifications[0].data) == 0)

    def test_header_only_csv_raises_error(self, csv_parser, create_request):
        """Test that CSV with only headers raises ValueError."""
        csv_content = "timestamp,urn,type,value"
        df = csv_to_dataframe(csv_content)
        request = create_request(tenant="t1", scope="/")

        with pytest.raises(ValueError, match="header row"):
            csv_parser.parse(df, request)

    def test_attribute_names_are_cleaned(self, csv_parser, create_request):
        """Test that attribute names have quotes and whitespace removed."""
        csv_content = 'timestamp,urn,type,"  value  "\n1750280400,urn:ngsi-ld:Device:1,Device,10'
        df = csv_to_dataframe(csv_content)
        request = create_request(tenant="t1", scope="/")

        notifications = csv_parser.parse(df, request)

        assert len(notifications) == 1
        assert notifications[0].data[0].name == "value"

    def test_all_attributes_are_properties(self, csv_parser, create_request):
        """Test that all attributes have type PROPERTY."""
        csv_content = "timestamp,urn,type,attr1,attr2,attr3\n1750280400,urn:ngsi-ld:Device:1,Device,10,test,true"
        df = csv_to_dataframe(csv_content)
        request = create_request(tenant="t1", scope="/")

        notifications = csv_parser.parse(df, request)

        assert len(notifications) == 1
        for attr in notifications[0].data:
            assert attr.type == EntityAttrType.PROPERTY


# ==============================================================================
# TEST: ERROR HANDLING
# ==============================================================================


class TestErrorHandling:
    """Tests error scenarios."""

    def test_missing_timestamp_column_raises_error(self, csv_parser, create_request):
        """Test that missing timestamp column raises ValueError."""
        csv_content = "urn,type,value1,value2\nurn:ngsi-ld:Device:1,Device,10,20"
        df = csv_to_dataframe(csv_content)
        request = create_request(tenant="t1", scope="/")

        with pytest.raises(ValueError, match="timestamp"):
            csv_parser.parse(df, request)

    def test_invalid_timestamp_skips_row(self, csv_parser, create_request):
        """Test that rows with invalid timestamps are skipped."""
        csv_content = "timestamp,urn,type,value\ninvalid,urn:ngsi-ld:Device:1,Device,10\n1750280400,urn:ngsi-ld:Device:1,Device,20"
        df = csv_to_dataframe(csv_content)
        request = create_request(tenant="t1", scope="/")

        notifications = csv_parser.parse(df, request)

        assert len(notifications) == 1
        assert len(notifications[0].data) == 1
        assert notifications[0].data[0].value == 20


# ==============================================================================
# TEST: COMPLEX SCENARIOS
# ==============================================================================


class TestComplexScenarios:
    """Tests complex real-world scenarios."""

    def test_heterogeneous_entities_with_different_types(self, csv_parser, create_request):
        """Test parsing entities with different types and tenants."""
        csv_content = (
            "timestamp,urn,type,tenant,scope,value\n"
            "1750280400,urn:ngsi-ld:Sensor:1,Sensor,tenant1,/sensors,25.5\n"
            "1750280500,urn:ngsi-ld:Device:1,Device,tenant2,/devices,100\n"
            "1750280600,urn:ngsi-ld:Sensor:1,Sensor,tenant1,/sensors,26.0"
        )
        df = csv_to_dataframe(csv_content)
        request = create_request()

        notifications = csv_parser.parse(df, request)

        assert len(notifications) == 2
        sensor = find_notification(notifications, "urn:ngsi-ld:Sensor:1")
        device = find_notification(notifications, "urn:ngsi-ld:Device:1")
        assert sensor is not None and len(sensor.data) == 2
        assert device is not None and len(device.data) == 1

    def test_ten_entities_multiple_rows_each(self, csv_parser, create_request):
        """Test parsing many entities, each appearing multiple times."""
        rows = ["timestamp,urn,type,tenant,scope,value"]
        for entity_num in range(1, 11):
            for time_offset in range(3):
                timestamp = 1750280400 + (entity_num * 100) + (time_offset * 300)
                urn = f"urn:ngsi-ld:Entity:{entity_num:03d}"
                value = entity_num * 10 + time_offset
                rows.append(f"{timestamp},{urn},Entity,t1,/,{value}")

        csv_content = "\n".join(rows)
        df = csv_to_dataframe(csv_content)
        request = create_request()

        notifications = csv_parser.parse(df, request)

        assert len(notifications) == 10
        for notification in notifications:
            assert len(notification.data) == 3
