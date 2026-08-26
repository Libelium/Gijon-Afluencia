"""
Edge case tests for CSV Parser.

Tests unusual scenarios, error conditions, and boundary cases:
- Missing or invalid data
- Case sensitivity and whitespace handling
- Special characters and encoding
- Large datasets
- Complex multi-entity scenarios
"""
import io
from typing import List

import pandas as pd
import pytest
from jobs.data.data_importation.parser.csv_parser import CsvParser
from schemas.data_importation_request import DataImportationRequest
from schemas.entity_data_notification import EntityDataNotification


@pytest.fixture
def csv_parser():
    """Fixture that provides a CsvParser instance for testing."""
    return CsvParser()


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


class TestCsvParserErrorHandling:
    """
    Tests error handling for invalid CSV inputs.
    Verifies that appropriate errors are raised for missing required columns,
    empty data, and other critical validation failures.
    """

    def test_csv_without_timestamp_column_raises_error(
        self, request_factory
    ):
        """Tests that CSV without a timestamp column raises a ValueError."""
        csv_content = '"urn","type","value","temperature"\n' "urn:ngsi-ld:Test:001,Test,10,25.5\n"
        request = request_factory()

        with pytest.raises(ValueError, match="timestamp"):
            parse_csv(csv_content, request)

    def test_csv_with_only_timestamp_column_raises_error(
        self, csv_parser, request_factory
    ):
        """Tests that CSV with only timestamp column (no attributes) raises a ValueError."""
        csv_content = '"timestamp"\n' "1750280400\n"
        request = request_factory()
        df = create_dataframe_from_csv(csv_content)

        with pytest.raises(ValueError, match="at least one attribute column"):
            csv_parser.parse(df, request)

    def test_empty_dataframe_raises_error(self, csv_parser, request_factory):
        """Tests that an empty DataFrame (no rows or columns) raises a ValueError."""
        request = request_factory()
        empty_df = pd.DataFrame()

        with pytest.raises(ValueError):
            csv_parser.parse(empty_df, request)


class TestCsvParserCaseInsensitivity:
    """
    Tests that column names are case-insensitive and whitespace-tolerant.
    Verifies that 'timestamp', 'TIMESTAMP', 'Timestamp', etc. are all recognized,
    and the same for metadata columns (urn, tenant, scope).
    """

    @pytest.mark.parametrize(
        "csv_content,request_params",
        [
            pytest.param(
                '"TIMESTAMP","urn","type","value"\n'
                "1750280400,urn:ngsi-ld:Test:001,Test,10\n",
                {
                    "tenant": "pid",
                    "scope": "/",
                },
                id="uppercase_timestamp",
            ),
            pytest.param(
                '"Timestamp","urn","type","value"\n'
                "1750280400,urn:ngsi-ld:Test:001,Test,10\n",
                {
                    "tenant": "pid",
                    "scope": "/",
                },
                id="capitalized_timestamp",
            ),
            pytest.param(
                '"  timestamp  ","urn","type","value"\n'
                "1750280400,urn:ngsi-ld:Test:001,Test,10\n",
                {
                    "tenant": "pid",
                    "scope": "/",
                },
                id="timestamp_with_spaces",
            ),
            pytest.param(
                '"timestamp","URN","TYPE","TENANT","SCOPE","value"\n'
                "1750280400,urn:ngsi-ld:Test:001,Test,tenant1,/scope1,10\n",
                {"tenant": None, "scope": None},
                id="uppercase_metadata_columns",
            ),
        ],
    )
    def test_case_insensitive_column_names(
        self, request_factory, csv_content, request_params
    ):
        """
        Tests that column names are recognized regardless of case or surrounding whitespace.
        Ensures parser handles TIMESTAMP, Timestamp, '  timestamp  ', URN, etc.
        """
        request = request_factory(**request_params)
        notifications = parse_csv(csv_content, request)

        assert len(notifications) >= 1
        assert len(notifications[0].data) >= 1


class TestCsvParserWhitespaceHandling:
    """
    Tests proper handling of whitespace in various contexts:
    - Leading/trailing spaces in column names
    - Leading/trailing spaces in values
    - Empty cells with only whitespace
    """

    @pytest.mark.parametrize(
        "csv_content,expected_attribute_count",
        [
            pytest.param(
                '"timestamp","urn","type","value","  empty1  ","empty2"\n'
                "1750280400,urn:ngsi-ld:Test:001,Test,10,  ,\n",
                1,
                id="empty_columns_with_spaces",
            ),
            pytest.param(
                '"timestamp","urn","type","value1","value2"\n'
                "1750280400,urn:ngsi-ld:Test:001,Test,  10  ,  20  \n",
                2,
                id="values_with_surrounding_spaces",
            ),
            pytest.param(
                '"timestamp","urn","type"," value "\n'
                "1750280400,urn:ngsi-ld:Test:001,Test,10\n",
                1,
                id="column_name_with_spaces",
            ),
        ],
    )
    def test_whitespace_handling(
        self, request_factory, csv_content, expected_attribute_count
    ):
        """
        Tests that whitespace is properly handled:
        - Empty columns (only spaces) are skipped
        - Values with surrounding spaces are trimmed
        - Column names with spaces are cleaned
        """
        request = request_factory()
        notifications = parse_csv(csv_content, request)

        assert len(notifications) == 1
        assert len(notifications[0].data) == expected_attribute_count


class TestCsvParserSpecialCharacters:
    """
    Tests handling of special characters and encoding:
    - Special characters in values (@, #, $, etc.)
    - CSV-quoted values with commas
    - Unicode characters
    """

    @pytest.mark.parametrize(
        "csv_content,expected_value",
        [
            pytest.param(
                '"timestamp","urn","type","special_chars"\n'
                "1750280400,urn:ngsi-ld:Test:001,Test,value@with#special$chars\n",
                "value@with#special$chars",
                id="special_characters_in_value",
            ),
            pytest.param(
                '"timestamp","urn","type","quoted_value"\n'
                '1750280400,urn:ngsi-ld:Test:001,Test,"text with, comma"\n',
                "text with, comma",
                id="quoted_value_with_comma",
            ),
            pytest.param(
                '"timestamp","urn","type","unicode"\n'
                "1750280400,urn:ngsi-ld:Test:001,Test,Ñoño\n",
                "Ñoño",
                id="unicode_characters",
            ),
        ],
    )
    def test_special_characters(
        self, request_factory, csv_content, expected_value
    ):
        """
        Tests that special characters are preserved correctly:
        - Special characters like @, #, $ in values
        - Quoted values containing commas
        - Unicode characters (e.g., Ñoño)
        """
        request = request_factory()
        notifications = parse_csv(csv_content, request)

        assert len(notifications) == 1
        assert notifications[0].data[0].value == expected_value


class TestCsvParserLargeDatasets:
    """
    Tests parser performance and correctness with large datasets.
    Verifies that the parser can handle hundreds or thousands of rows
    without errors or data loss.
    """

    @pytest.mark.parametrize(
        "row_count",
        [
            pytest.param(100, id="100_rows"),
            pytest.param(1000, id="1000_rows"),
        ],
    )
    def test_large_csv_files(self, request_factory, row_count):
        """
        Tests parser with large CSV files (100+ and 1000+ rows).
        Ensures all rows are processed correctly and no data is lost.
        """
        csv_lines = ['"timestamp","urn","type","value"']

        for i in range(row_count):
            timestamp = 1750280400 + i
            value = 10 + i * 0.1
            csv_lines.append(f"{timestamp},urn:ngsi-ld:Test:001,Test,{value}")

        csv_content = "\n".join(csv_lines)
        request = request_factory()
        notifications = parse_csv(csv_content, request)

        assert len(notifications) == 1
        assert len(notifications[0].data) == row_count


class TestCsvParserComplexScenarios:
    """
    Tests complex real-world scenarios:
    - Multiple entities with interleaved rows
    - Multiple attributes per timestamp
    - Mixed timestamp formats
    These tests verify the parser's ability to handle production-like data.
    """

    def test_multiple_entities_with_different_timestamps(
        self, request_factory
    ):
        """
        Tests parsing CSV with multiple entities interleaved in the data.
        Verifies that rows are correctly grouped by entity URN and that
        each entity's attributes are collected across multiple timestamps.
        """
        csv_content = (
            '"timestamp","urn","type","value"\n'
            "1750280400,urn:ngsi-ld:Device:001,Device,10\n"
            "1750280500,urn:ngsi-ld:Device:002,Device,20\n"
            "1750280600,urn:ngsi-ld:Device:001,Device,15\n"
            "1750280700,urn:ngsi-ld:Device:002,Device,25\n"
        )
        request = request_factory(tenant="pid", scope="/")
        notifications = parse_csv(csv_content, request)

        assert len(notifications) == 2

        device_001 = next(n for n in notifications if n.urn == "urn:ngsi-ld:Device:001")
        device_002 = next(n for n in notifications if n.urn == "urn:ngsi-ld:Device:002")

        assert len(device_001.data) == 2
        assert len(device_002.data) == 2

    def test_multiple_attributes_per_timestamp(self, request_factory):
        """
        Tests that multiple attributes in a single row are all correctly parsed
        and each receives the same timestamp from that row.
        """
        csv_content = (
            '"timestamp","urn","type","temperature","humidity","pressure"\n'
            "1750280400,urn:ngsi-ld:Test:001,Test,20.5,65,1013.25\n"
            "1750280500,urn:ngsi-ld:Test:001,Test,21.0,63,1013.5\n"
        )
        request = request_factory()
        notifications = parse_csv(csv_content, request)

        assert len(notifications) == 1
        assert len(notifications[0].data) == 6

        timestamps = set(attr.timestamp for attr in notifications[0].data)
        assert len(timestamps) == 2

    def test_mixed_timestamp_formats(self, request_factory):
        """
        Tests that the parser can handle mixed timestamp formats in a single CSV:
        - Unix timestamps (1750280400)
        - ISO format timestamps (2025-06-18 14:55:30)
        All timestamps should be converted to float format.
        """
        csv_content = (
            '"timestamp","urn","type","value"\n'
            "1750280400,urn:ngsi-ld:Test:001,Test,10\n"
            "2025-06-18 14:55:30,urn:ngsi-ld:Test:001,Test,20\n"
            "1750280600,urn:ngsi-ld:Test:001,Test,30\n"
        )
        request = request_factory()
        notifications = parse_csv(csv_content, request)

        assert len(notifications) == 1
        assert len(notifications[0].data) == 3

        timestamps = [attr.timestamp for attr in notifications[0].data]
        assert all(isinstance(ts, float) for ts in timestamps)


class TestCsvParserDataIntegrity:
    """
    Tests data integrity and preservation during parsing:
    - Attribute order preservation
    - Handling of failed rows
    - Duplicate timestamp handling
    Ensures no data is lost or corrupted during parsing.
    """

    def test_attribute_ordering_preserved(self, request_factory):
        """
        Tests that the order of attributes in the CSV columns is preserved
        in the parsed output. Important for predictable data processing.
        """
        csv_content = (
            '"timestamp","urn","type","attr_a","attr_b","attr_c"\n'
            "1750280400,urn:ngsi-ld:Test:001,Test,1,2,3\n"
        )
        request = request_factory()
        notifications = parse_csv(csv_content, request)

        attribute_names = [attr.name for attr in notifications[0].data]
        assert attribute_names == ["attr_a", "attr_b", "attr_c"]

    def test_all_rows_processed_when_some_fail(self, request_factory):
        """
        Tests that when some rows have invalid data (e.g., invalid timestamps),
        those rows are skipped but other valid rows are still processed.
        Ensures partial failures don't cause complete parsing failure.
        """
        csv_content = (
            '"timestamp","urn","type","value"\n'
            "1750280400,urn:ngsi-ld:Test:001,Test,10\n"
            "invalid_timestamp,urn:ngsi-ld:Test:001,Test,20\n"
            "1750280600,urn:ngsi-ld:Test:001,Test,30\n"
        )
        request = request_factory()
        notifications = parse_csv(csv_content, request)

        assert len(notifications) == 1
        assert len(notifications[0].data) == 2

        values = [attr.value for attr in notifications[0].data]
        assert values == [10, 30]

    def test_duplicate_timestamps_preserved(self, request_factory):
        """
        Tests that multiple rows with the same timestamp are all preserved.
        Each row should create separate attributes even if timestamps are identical.
        """
        csv_content = (
            '"timestamp","urn","type","sensor_a","sensor_b"\n'
            "1750280400,urn:ngsi-ld:Test:001,Test,10,20\n"
            "1750280400,urn:ngsi-ld:Test:001,Test,15,25\n"
        )
        request = request_factory()
        notifications = parse_csv(csv_content, request)

        assert len(notifications) == 1
        assert len(notifications[0].data) == 4

        timestamps = [attr.timestamp for attr in notifications[0].data]
        assert timestamps == [1750280400.0] * 4
