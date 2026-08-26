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


@pytest.fixture
def request_factory():
    """
    Factory fixture that creates DataImportationRequest objects with customizable parameters.
    Provides default values for common test scenarios.
    """
    def _factory(
        tenant="pid",
        scope="/",
    ):
        return DataImportationRequest(
            user_id=1,
            tenant=tenant,
            scope=scope,
            storage_file_path="test.csv",
        )

    return _factory


def create_dataframe_from_csv(csv_content: str) -> pd.DataFrame:
    """
    Helper function that converts CSV string content to a pandas DataFrame.
    Uses the same settings as the parser to ensure consistent behavior.
    """
    return pd.read_csv(
        io.StringIO(csv_content),
        skipinitialspace=True,
        encoding="utf-8",
        dtype=str,
        keep_default_na=False,
    )


def parse_csv(
    csv_content: str, request: DataImportationRequest
) -> List[EntityDataNotification]:
    """
    Helper function that performs the full CSV parsing workflow:
    1. Converts CSV string to DataFrame
    2. Creates parser instance
    3. Parses DataFrame with request metadata
    4. Returns list of entity notifications
    """
    parser = CsvParser()
    df = create_dataframe_from_csv(csv_content)
    return parser.parse(df, request)


class TestCsvParserBasicFunctionality:
    """
    Tests basic CSV parsing functionality with standard inputs.
    Covers common scenarios like numeric values, single/multiple attributes,
    and single/multiple rows.
    """

    @pytest.mark.parametrize(
        "csv_content,request_params,expected_notifications",
        [
            pytest.param(
                '"timestamp","urn","type","temperature","humidity"\n'
                "1750258530,urn:ngsi-ld:Test:001,Test,25.5,60\n"
                "1750280730,urn:ngsi-ld:Test:001,Test,26,62.1\n",
                {
                    "tenant": "pid",
                    "scope": "/",
                },
                [
                    EntityDataNotification(
                        urn="urn:ngsi-ld:Test:001",
                        tenant="pid",
                        scope="/",
                        type="Test",
                        notified_at=None,
                        data=[
                            EntityAttr(
                                name="temperature",
                                value=25.5,
                                timestamp=1750258530.0,
                                type=EntityAttrType.PROPERTY,
                            ),
                            EntityAttr(
                                name="humidity",
                                value=60,
                                timestamp=1750258530.0,
                                type=EntityAttrType.PROPERTY,
                            ),
                            EntityAttr(
                                name="temperature",
                                value=26,
                                timestamp=1750280730.0,
                                type=EntityAttrType.PROPERTY,
                            ),
                            EntityAttr(
                                name="humidity",
                                value=62.1,
                                timestamp=1750280730.0,
                                type=EntityAttrType.PROPERTY,
                            ),
                        ],
                    )
                ],
                id="basic_csv_with_numeric_timestamps",
            ),
            pytest.param(
                '"timestamp","urn","type","value"\n'
                "1750280400,urn:ngsi-ld:Sensor:001,Sensor,10\n"
                "1750280700,urn:ngsi-ld:Sensor:001,Sensor,30\n",
                {
                    "tenant": "tenant1",
                    "scope": "/scope1",
                },
                [
                    EntityDataNotification(
                        urn="urn:ngsi-ld:Sensor:001",
                        tenant="tenant1",
                        scope="/scope1",
                        type="Sensor",
                        notified_at=None,
                        data=[
                            EntityAttr(
                                name="value",
                                value=10,
                                timestamp=1750280400.0,
                                type=EntityAttrType.PROPERTY,
                            ),
                            EntityAttr(
                                name="value",
                                value=30,
                                timestamp=1750280700.0,
                                type=EntityAttrType.PROPERTY,
                            ),
                        ],
                    )
                ],
                id="simple_single_attribute",
            ),
            pytest.param(
                '"timestamp","urn","type","temp","humidity","pressure"\n'
                "1750280400,urn:ngsi-ld:Weather:001,Weather,20.5,65,1013.25\n",
                {
                    "tenant": "pid",
                    "scope": "/",
                },
                [
                    EntityDataNotification(
                        urn="urn:ngsi-ld:Weather:001",
                        tenant="pid",
                        scope="/",
                        type="Weather",
                        notified_at=None,
                        data=[
                            EntityAttr(
                                name="temp",
                                value=20.5,
                                timestamp=1750280400.0,
                                type=EntityAttrType.PROPERTY,
                            ),
                            EntityAttr(
                                name="humidity",
                                value=65,
                                timestamp=1750280400.0,
                                type=EntityAttrType.PROPERTY,
                            ),
                            EntityAttr(
                                name="pressure",
                                value=1013.25,
                                timestamp=1750280400.0,
                                type=EntityAttrType.PROPERTY,
                            ),
                        ],
                    )
                ],
                id="multiple_attributes_single_row",
            ),
        ],
    )
    def test_parse_csv_basic(
        self,
        request_factory,
        csv_content,
        request_params,
        expected_notifications,
    ):
        """
        Tests basic CSV parsing with various configurations:
        - Single and multiple rows
        - Single and multiple attributes
        - Numeric timestamp values
        Verifies that parsed data matches expected structure and values.
        """
        request = request_factory(**request_params)
        notifications = parse_csv(csv_content, request)

        assert len(notifications) == len(expected_notifications)

        for actual, expected in zip(notifications, expected_notifications):
            assert actual.urn == expected.urn
            assert actual.tenant == expected.tenant
            assert actual.scope == expected.scope
            assert actual.type == expected.type
            assert len(actual.data) == len(expected.data)

            for actual_attr, expected_attr in zip(actual.data, expected.data):
                assert actual_attr.name == expected_attr.name
                assert actual_attr.value == expected_attr.value
                assert actual_attr.timestamp == expected_attr.timestamp
                assert actual_attr.type == expected_attr.type


class TestCsvParserValueTypes:
    """
    Tests correct parsing and type inference for different value types.
    Verifies that integers, floats, booleans, strings, and JSON objects
    are parsed into their appropriate Python types.
    """

    @pytest.mark.parametrize(
        "csv_content,request_params,expected_values",
        [
            pytest.param(
                '"timestamp","urn","type","int_val","float_val","string_val"\n'
                "1750280400,urn:ngsi-ld:Test:001,Test,123,45.67,hello\n",
                {
                    "tenant": "pid",
                    "scope": "/",
                },
                [123, 45.67, "hello"],
                id="mixed_value_types",
            ),
            pytest.param(
                '"timestamp","urn","type","bool_true","bool_false"\n'
                "1750280400,urn:ngsi-ld:Test:001,Test,true,false\n",
                {
                    "tenant": "pid",
                    "scope": "/",
                },
                [True, False],
                id="boolean_values",
            ),
            pytest.param(
                '"timestamp","urn","type","negative","positive"\n'
                "1750280400,urn:ngsi-ld:Test:001,Test,-50.5,100\n",
                {
                    "tenant": "pid",
                    "scope": "/",
                },
                [-50.5, 100],
                id="negative_and_positive_numbers",
            ),
            pytest.param(
                '"timestamp","urn","type","json_obj"\n'
                '1750280400,urn:ngsi-ld:Test:001,Test,"{""a"": 1, ""b"": ""test""}"\n',
                {
                    "tenant": "pid",
                    "scope": "/",
                },
                [{"a": 1, "b": "test"}],
                id="json_object_value",
            ),
        ],
    )
    def test_parse_csv_value_types(
        self,
        request_factory,
        csv_content,
        request_params,
        expected_values,
    ):
        """
        Tests that different value types are correctly parsed:
        - Mixed types (integers, floats, strings)
        - Boolean values (true/false)
        - Negative and positive numbers
        - JSON objects embedded in CSV
        """
        request = request_factory(**request_params)
        notifications = parse_csv(csv_content, request)

        assert len(notifications) == 1
        actual_values = [attr.value for attr in notifications[0].data]
        assert actual_values == expected_values


class TestCsvParserMetadataOverride:
    """
    Tests the priority system for metadata (urn, tenant, scope, type).
    URN and type always come from file.
    Request tenant/scope override file values when present.
    File metadata is used as fallback when request has no values.
    """

    @pytest.mark.parametrize(
        "csv_content,request_params,expected_urn,expected_tenant,expected_scope,expected_type",
        [
            pytest.param(
                '"timestamp","urn","type","tenant","scope","value"\n'
                "1750280400,urn:ngsi-ld:FromCSV:001,FromCSV,csv_tenant,/csv_scope,10\n",
                {
                    "tenant": "request_tenant",
                    "scope": "/request_scope",
                },
                "urn:ngsi-ld:FromCSV:001",
                "request_tenant",
                "/request_scope",
                "FromCSV",
                id="request_metadata_overrides_csv",
            ),
            pytest.param(
                '"timestamp","urn","type","tenant","scope","value"\n'
                "1750280400,urn:ngsi-ld:FromCSV:001,FromCSV,csv_tenant,/csv_scope,10\n",
                {
                    "tenant": None,
                    "scope": None,
                },
                "urn:ngsi-ld:FromCSV:001",
                "csv_tenant",
                "/csv_scope",
                "FromCSV",
                id="csv_metadata_when_request_is_none",
            ),
            pytest.param(
                '"timestamp","urn","type","value"\n'
                "1750280400,urn:ngsi-ld:FromFile:001,FromFile,10\n",
                {
                    "tenant": "request_tenant",
                    "scope": "/request_scope",
                },
                "urn:ngsi-ld:FromFile:001",
                "request_tenant",
                "/request_scope",
                "FromFile",
                id="request_metadata_when_csv_has_none",
            ),
        ],
    )
    def test_metadata_priority(
        self,
        request_factory,
        csv_content,
        request_params,
        expected_urn,
        expected_tenant,
        expected_scope,
        expected_type,
    ):
        """
        Tests metadata priority rules:
        1. URN and type always come from CSV file
        2. Request tenant/scope overrides CSV metadata when both exist
        3. CSV metadata is used as fallback when request has no values
        """
        request = request_factory(**request_params)
        notifications = parse_csv(csv_content, request)

        assert len(notifications) == 1
        assert notifications[0].urn == expected_urn
        assert notifications[0].tenant == expected_tenant
        assert notifications[0].scope == expected_scope
        assert notifications[0].type == expected_type


class TestCsvParserMultipleEntities:
    """
    Tests parsing CSV files that contain data for multiple entities.
    Verifies that rows are correctly grouped by entity key (urn, tenant, etc.)
    and that multiple entities produce separate notifications.
    """

    @pytest.mark.parametrize(
        "csv_content,request_params,expected_entity_count",
        [
            pytest.param(
                '"timestamp","urn","type","value"\n'
                "1750280400,urn:ngsi-ld:Device:001,Device,10\n"
                "1750280500,urn:ngsi-ld:Device:002,Device,20\n"
                "1750280600,urn:ngsi-ld:Device:001,Device,15\n",
                {
                    "tenant": "pid",
                    "scope": "/",
                },
                2,
                id="multiple_entities_from_csv_urn_column",
            ),
            pytest.param(
                '"timestamp","urn","type","tenant","value"\n'
                "1750280400,urn:ngsi-ld:Device:001,Device,tenant1,10\n"
                "1750280500,urn:ngsi-ld:Device:001,Device,tenant2,20\n"
                "1750280600,urn:ngsi-ld:Device:001,Device,tenant1,15\n",
                {
                    "tenant": None,
                    "scope": "/",
                },
                2,
                id="multiple_entities_from_csv_tenant_column",
            ),
        ],
    )
    def test_parse_multiple_entities(
        self,
        request_factory,
        csv_content,
        request_params,
        expected_entity_count,
    ):
        """
        Tests that CSV files with multiple entities (identified by different
        URNs or tenants) are correctly parsed into separate notifications.
        Each unique entity combination should produce one notification.
        """
        request = request_factory(**request_params)
        notifications = parse_csv(csv_content, request)

        assert len(notifications) == expected_entity_count


class TestCsvParserEmptyAndMalformed:
    """
    Tests parser behavior with problematic inputs:
    - Empty CSV files (header only)
    - Malformed rows (missing values)
    - Empty/whitespace values
    Verifies error handling and data skipping behavior.
    """

    @pytest.mark.parametrize(
        "csv_content,request_params,expected_data_count,should_raise",
        [
            pytest.param(
                '"timestamp","urn","type","value"\n',
                {
                    "tenant": "pid",
                    "scope": "/",
                },
                None,
                True,
                id="header_only_csv_raises_error",
            ),
            pytest.param(
                '"timestamp","urn","type","value"\n'
                "1750280400,urn:ngsi-ld:Test:001,Test,10\n"
                "1750280500\n"
                "1750280600,urn:ngsi-ld:Test:001,Test,30\n",
                {
                    "tenant": "pid",
                    "scope": "/",
                },
                2,
                False,
                id="malformed_row_skipped",
            ),
            pytest.param(
                '"timestamp","urn","type","value","empty_col"\n'
                "1750280400,urn:ngsi-ld:Test:001,Test,10,\n"
                "1750280500,urn:ngsi-ld:Test:001,Test,20,  \n",
                {
                    "tenant": "pid",
                    "scope": "/",
                },
                2,
                False,
                id="empty_values_skipped",
            ),
        ],
    )
    def test_empty_and_malformed(
        self,
        request_factory,
        csv_content,
        request_params,
        expected_data_count,
        should_raise,
    ):
        """
        Tests error handling for invalid CSV data:
        - Header-only CSV should raise ValueError
        - Malformed rows (missing values) should be skipped gracefully
        - Empty values should be skipped and not create attributes
        """
        request = request_factory(**request_params)

        if should_raise:
            with pytest.raises(ValueError):
                parse_csv(csv_content, request)
        else:
            notifications = parse_csv(csv_content, request)
            total_attributes = sum(len(n.data) for n in notifications)
            assert total_attributes == expected_data_count
