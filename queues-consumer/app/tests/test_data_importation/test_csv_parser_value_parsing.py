"""
Value parsing tests for CSV Parser.

Tests the internal value parsing logic to ensure correct type inference:
- Numeric values (integers, floats, negative numbers)
- Boolean values (true/false in various cases)
- JSON values (objects and arrays)
- String values
- Timestamp parsing
- Attribute name cleaning
"""
from typing import Any

import pytest
from jobs.data.data_importation.parser.csv_parser import CsvParser


@pytest.fixture
def csv_parser():
    """Fixture that provides a CsvParser instance for testing."""
    return CsvParser()


def parse_single_value(value_str: str, csv_parser: CsvParser) -> Any:
    """
    Helper function that directly calls the parser's internal _parse_value method.
    Used for unit testing the value parsing logic in isolation.
    """
    return csv_parser._parse_value(value_str)


class TestValueParsing:
    """
    Tests numeric value parsing and type inference.
    Verifies that integer and float values are correctly identified,
    including edge cases like negative numbers, zero, and values with whitespace.
    """

    @pytest.mark.parametrize(
        "input_value,expected_output,expected_type",
        [
            pytest.param("76.1", 76.1, float, id="float_value"),
            pytest.param("123", 123, int, id="integer_value"),
            pytest.param("-50.5", -50.5, float, id="negative_float"),
            pytest.param("-100", -100, int, id="negative_integer"),
            pytest.param("  42  ", 42, int, id="integer_with_whitespace"),
            pytest.param("3.14159", 3.14159, float, id="pi_value"),
            pytest.param("0", 0, int, id="zero"),
            pytest.param("21 mg", "21 mg", str, id="number_with_unit_suffix"),
            pytest.param("123 abc", "123 abc", str, id="number_with_text_suffix"),
        ],
    )
    def test_parse_numeric_values(
        self, csv_parser, input_value, expected_output, expected_type
    ):
        """
        Tests parsing of numeric values:
        - Floats (76.1, 3.14159)
        - Integers (123, 0, 42)
        - Negative numbers (-50.5, -100)
        - Numbers with whitespace
        - Numbers with text suffixes (treated as strings)
        """
        result = parse_single_value(input_value, csv_parser)
        assert result == expected_output
        assert type(result) == expected_type


class TestBooleanParsing:
    """
    Tests boolean value parsing.
    Verifies that true/false strings are recognized in various cases
    (lowercase, uppercase, capitalized) and with whitespace.
    """

    @pytest.mark.parametrize(
        "input_value,expected_output",
        [
            pytest.param("true", True, id="lowercase_true"),
            pytest.param("false", False, id="lowercase_false"),
            pytest.param("True", True, id="capitalized_true"),
            pytest.param("False", False, id="capitalized_false"),
            pytest.param("TRUE", True, id="uppercase_true"),
            pytest.param("FALSE", False, id="uppercase_false"),
            pytest.param("  true  ", True, id="true_with_whitespace"),
            pytest.param("  false  ", False, id="false_with_whitespace"),
        ],
    )
    def test_parse_boolean_values(self, csv_parser, input_value, expected_output):
        """
        Tests that boolean values are correctly parsed:
        - Lowercase: true, false
        - Uppercase: TRUE, FALSE
        - Capitalized: True, False
        - With surrounding whitespace
        """
        result = parse_single_value(input_value, csv_parser)
        assert result == expected_output
        assert type(result) == bool


class TestJsonParsing:
    """
    Tests JSON value parsing.
    Verifies that valid JSON strings are parsed into Python objects/arrays,
    and that malformed JSON is kept as a string.
    """

    @pytest.mark.parametrize(
        "input_value,expected_output",
        [
            pytest.param(
                '{"a": 1, "b": "test"}', {"a": 1, "b": "test"}, id="simple_json_object"
            ),
            pytest.param(
                '  { "a" : 1 }  ', {"a": 1}, id="json_object_with_whitespace"
            ),
            pytest.param('[1, 2, 3]', [1, 2, 3], id="json_array"),
            pytest.param(
                '{"nested": {"key": "value"}}',
                {"nested": {"key": "value"}},
                id="nested_json_object",
            ),
            pytest.param('{"a": 1,', '{"a": 1,', id="malformed_json_as_string"),
            pytest.param('[1, 2,', '[1, 2,', id="malformed_array_as_string"),
        ],
    )
    def test_parse_json_values(self, csv_parser, input_value, expected_output):
        """
        Tests that JSON values are correctly parsed:
        - Simple JSON objects: {"a": 1, "b": "test"}
        - JSON arrays: [1, 2, 3]
        - Nested JSON objects
        - JSON with whitespace
        - Malformed JSON (kept as string)
        """
        result = parse_single_value(input_value, csv_parser)
        assert result == expected_output


class TestStringParsing:
    """
    Tests string value parsing.
    Verifies that regular text values are handled correctly,
    including whitespace trimming and special characters.
    """

    @pytest.mark.parametrize(
        "input_value,expected_output",
        [
            pytest.param("abc", "abc", id="simple_string"),
            pytest.param("hello world", "hello world", id="string_with_space"),
            pytest.param(
                "not a number 123", "not a number 123", id="text_before_number"
            ),
            pytest.param("  text  ", "text", id="string_with_whitespace_stripped"),
            pytest.param("", "", id="empty_string"),
            pytest.param("special@chars#123", "special@chars#123", id="special_chars"),
        ],
    )
    def test_parse_string_values(self, csv_parser, input_value, expected_output):
        """
        Tests that string values are correctly parsed:
        - Simple strings
        - Strings with spaces
        - Text mixed with numbers
        - Strings with surrounding whitespace (trimmed)
        - Empty strings
        - Special characters
        """
        result = parse_single_value(input_value, csv_parser)
        assert result == expected_output
        assert type(result) == str


class TestNonStringInputs:
    """
    Tests that non-string inputs (already parsed types) are passed through unchanged.
    This handles cases where values are already in their native Python types.
    """

    @pytest.mark.parametrize(
        "input_value,expected_output",
        [
            pytest.param(123, 123, id="integer_passthrough"),
            pytest.param(45.67, 45.67, id="float_passthrough"),
            pytest.param(True, True, id="boolean_passthrough"),
        ],
    )
    def test_non_string_inputs_passthrough(
        self, csv_parser, input_value, expected_output
    ):
        """
        Tests that values that are already Python types (int, float, bool)
        are passed through unchanged without re-parsing.
        """
        result = parse_single_value(input_value, csv_parser)
        assert result == expected_output


class TestTimestampParsing:
    """
    Tests timestamp parsing functionality.
    Verifies that various timestamp formats (Unix, ISO) are correctly
    converted to float values for internal use.
    """

    @pytest.mark.parametrize(
        "input_timestamp,expected_output",
        [
            pytest.param("1750280730", 1750280730.0, id="unix_timestamp_string"),
            pytest.param("1750280730.5", 1750280730.5, id="unix_timestamp_with_decimal"),
        ],
    )
    def test_parse_timestamps(self, csv_parser, input_timestamp, expected_output):
        """
        Tests parsing of Unix timestamp formats:
        - Integer Unix timestamps (1750280730)
        - Float Unix timestamps with decimals (1750280730.5)
        """
        result = csv_parser._parse_timestamp(input_timestamp)
        assert result == expected_output

    def test_parse_iso_timestamp(self, csv_parser):
        """
        Tests parsing of ISO format timestamps (2025-06-18T14:55:30).
        Verifies that ISO timestamps are converted to Unix float format.
        """
        result = csv_parser._parse_timestamp("2025-06-18T14:55:30")
        assert isinstance(result, float)
        assert result > 0


class TestTimestampParsingErrors:
    """
    Tests error handling for invalid timestamp values.
    Verifies that unparseable timestamps raise appropriate errors.
    """

    @pytest.mark.parametrize(
        "invalid_timestamp",
        [
            pytest.param("not a timestamp", id="invalid_text"),
            pytest.param("abc123", id="alphanumeric"),
            pytest.param("", id="empty_string"),
        ],
    )
    def test_invalid_timestamps_raise_error(self, csv_parser, invalid_timestamp):
        """
        Tests that invalid timestamp values (text, alphanumeric, empty strings)
        raise ValueError when attempting to parse.
        """
        with pytest.raises(ValueError):
            csv_parser._parse_timestamp(invalid_timestamp)


class TestAttributeNameCleaning:
    """
    Tests attribute name cleaning functionality.
    Verifies that quotes and whitespace are removed from column names
    to produce clean attribute names.
    """

    @pytest.mark.parametrize(
        "input_name,expected_output",
        [
            pytest.param('"temperature"', "temperature", id="quoted_name"),
            pytest.param("  humidity  ", "humidity", id="name_with_whitespace"),
            pytest.param('"  pressure  "', "pressure", id="quoted_with_whitespace"),
            pytest.param("value", "value", id="clean_name"),
        ],
    )
    def test_clean_attribute_names(self, csv_parser, input_name, expected_output):
        """
        Tests that attribute names are cleaned properly:
        - Removes surrounding quotes
        - Trims whitespace
        - Handles combination of quotes and whitespace
        """
        result = csv_parser._clean_attribute_name(input_name)
        assert result == expected_output
