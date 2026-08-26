import json
from datetime import datetime
from typing import Any, List, Tuple

import dateutil.parser
import pandas as pd
from config.logging import appLogging as logging
from jobs.data.data_importation.parser.parser import DataParser
from schemas.data_importation_request import DataImportationRequest
from schemas.entity_data_notification import (
    EntityAttr,
    EntityAttrType,
    EntityDataNotification,
)
from utils.ngsi.ngsi_ld_utils import  is_valid_ngsi_ld_urn


class DataFrameParser(DataParser):
    """
    Generic parser that converts a pandas DataFrame into a list of
    EntityDataNotification objects.

    Expected DataFrame structure:
    - Must contain a column named "timestamp" (case-insensitive)
      • Values may be numeric (Unix epoch) or ISO 8601 strings
    - May contain metadata columns for entity identification:
      • urn, tenant, scope, type (optional but recommended)
      • If missing, values will be obtained from the DataImportationRequest,
        currently the data importation request only accepts enough params to 
        upload data to one entity.
     - All other columns are treated as attributes of the entity

    Parsing behavior:
    - Each row represents a set of attribute values at a given timestamp
    - Rows are grouped by entity key (urn, tenant, scope, type)
    - One EntityDataNotification is generated per entity with all attributes collected
    
    This parser enables processing of multiple file formats (CSV, KML, JSON...)
    once they are converted to a DataFrame with the expected structure.
    """
    
    def parse(
        self,
        df: pd.DataFrame,
        request: DataImportationRequest,
    ) -> List[EntityDataNotification]:
        """
        Process a DataFrame and generate entity data notifications.

        Args:
            df: A pandas DataFrame with structured data
            request: Provides default metadata values for the entity

        Returns:
            A list of EntityDataNotification grouped by entity key

        Raises:
            ValueError: If mandatory columns are missing or structure is invalid
            Exception: Any unexpected parsing error is logged and re-raised
        """
        try:
            self._validate_dataframe(df)
            return self._extract_notifications(df, "DataFrame", request)
        except Exception as e:
            logging.error(f"Failed to parse DataFrame: {e}", exc_info=True)
            raise

    def _validate_dataframe(self, df: pd.DataFrame) -> None:
        """Validate that DataFrame has minimum required structure."""
        if df.empty or df.shape[1] < 2:
            raise ValueError(
                "CSV must have a header row with at least one attribute column."
            )

    def _extract_notifications(
        self, df: pd.DataFrame, file_path: str, request: DataImportationRequest
    ) -> List[EntityDataNotification]:
        """
        Extract entity data notifications from DataFrame rows.
        Groups rows by entity (urn, tenant, scope, type) and creates one notification per entity.
        """
        column_info = self._identify_columns(df)

        entity_attributes = {}
        for idx, row in df.iterrows():
            entity_key, attributes = self._process_row(
                row, idx, column_info, file_path, request
            )

            if entity_key:
                if entity_key not in entity_attributes:
                    entity_attributes[entity_key] = {"attributes": []}
                entity_attributes[entity_key]["attributes"].extend(attributes)
        
        return self._build_notifications_from_groups(entity_attributes)

    def _identify_columns(self, df: pd.DataFrame) -> dict:
        """
        Identify and categorize DataFrame columns in a single pass.
        Returns dict with: timestamp column, metadata columns, and attribute columns.
        """
        METADATA_COLUMNS = {"urn", "tenant", "scope", "type"}

        # Initialize column containers
        timestamp_col = None
        metadata_cols = {}
        attribute_cols = []

        # Categorize each column
        for col in df.columns:
            col_lower = col.strip().lower()

            if col_lower == "timestamp":
                timestamp_col = col
            elif col_lower in METADATA_COLUMNS:
                metadata_cols[col_lower] = col
            else:
                attribute_cols.append(col)

        # Validate timestamp column exists
        if timestamp_col is None:
            raise ValueError(
                "CSV must have a column with 'timestamp' header (case-insensitive)."
            )

        return {
            "timestamp": timestamp_col,
            "metadata": metadata_cols,
            "attributes": attribute_cols,
        }

    def _build_notifications_from_groups(
        self, entity_attributes: dict
    ) -> List[EntityDataNotification]:
        """
        Convert grouped entity attributes into notifications.
        Creates one notification per unique entity with all its attributes.
        """
        notifications = []

        for (urn, tenant, scope, type_), entity_data in entity_attributes.items():
            notification = EntityDataNotification(
                urn=urn,
                tenant=tenant,
                scope=scope,
                type=type_,
                notified_at=datetime.now().timestamp(),
                data=entity_data["attributes"],
            )
            notifications.append(notification)

        return notifications
    
    def _process_row(
        self,
        row: pd.Series,
        row_index: int,
        column_info: dict,
        file_path: str,
        request: DataImportationRequest,
    ) -> tuple[tuple | None, List[EntityAttr]]:
        """
        Process a single CSV row to extract entity key and attributes.
        Returns tuple of (entity_key, attributes) or (None, []) if error.
        """
        try:
            # Parse timestamp for this row
            timestamp = self._parse_timestamp(row[column_info["timestamp"]])
            # Extract all attributes from the row
            attributes = self._extract_row_attributes(
                row, column_info["attributes"], timestamp
            )
            # Determine entity key for grouping
            entity_key = self._extract_entity_key(row, column_info["metadata"], request)

            return entity_key, attributes

        except Exception as e:
            self._log_row_error(row_index, file_path, e)
            return None, []

    def _extract_entity_key(
        self, row: pd.Series, metadata_cols: dict, request: DataImportationRequest
    ) -> tuple:
        """
        Extract entity key tuple for grouping notifications.
        - urn: always from file (required)
        - type: always from file (required)
        - tenant/scope: from request if present, otherwise from file
        Returns (urn, tenant, scope, type).
        """
        urn = self._get_csv_value(row, metadata_cols, "urn")
        if not urn:
            raise ValueError("Missing required 'urn' value in row")
        if not is_valid_ngsi_ld_urn(urn):
            raise ValueError(f"Invalid NGSI-LD URN format: '{urn}'. Expected format: 'urn:ngsi-ld:<type>:<id>'")
        type_ = self._get_csv_value(row, metadata_cols, "type")
        if not type_:
            raise ValueError("Missing required 'type' value in row")
        tenant = request.tenant or self._get_csv_value(row, metadata_cols, "tenant")  
        scope = request.scope or self._get_csv_value(row, metadata_cols, "scope")  

        if bool(tenant) != bool(scope):
            raise ValueError("Both 'tenant' and 'scope' must be provided together or neither")

        return (urn, tenant, scope, type_)

    def _get_csv_value(
        self, row: pd.Series, metadata_cols: dict, key: str
    ) -> str | None:
        """
        Get metadata value from CSV row if the column exists.
        Returns None if column doesn't exist or value is empty.
        """
        if key in metadata_cols:
            value = row[metadata_cols[key]]
            return value if value and value.strip() else None

        return None

    def _log_row_error(self, row_index: int, file_path: str, error: Exception) -> None:
        """Log warning for malformed CSV row and continue processing."""
        line_number = row_index + 2  # +1 for 1-based, +1 for header

        logging.warning(
            f"Skipping malformed CSV row {line_number} in {file_path}: {error}"
        )

    def _extract_row_attributes(
        self, row: pd.Series, attribute_cols: List[str], timestamp: float
    ) -> List[EntityAttr]:
        """
        Extract all valid attributes from a single row.
        Skips empty values.
        """
        attributes = []

        for attr_name in attribute_cols:
            attribute = self._create_attribute_if_valid(
                attr_name, row[attr_name], timestamp
            )
            if attribute:
                attributes.append(attribute)

        return attributes

    def _create_attribute_if_valid(
        self, attr_name: str, value_str: str, timestamp: float
    ) -> EntityAttr | None:
        """
        Create an EntityAttr if the value is valid.
        Returns None for empty or whitespace-only values.
        """
        # Skip empty values
        if not value_str or not value_str.strip():
            return None

        # Parse and clean the attribute
        parsed_value = self._parse_value(value_str)
        clean_name = self._clean_attribute_name(attr_name)

        return EntityAttr(
            name=clean_name,
            value=parsed_value,
            timestamp=timestamp,
            type=EntityAttrType.PROPERTY,
        )

    def _parse_timestamp(self, ts_str: str) -> float:
        """
        Parse timestamp string to Unix timestamp (float).
        Supports numeric values and ISO 8601 date strings.
        """
        timestamp = self._try_parse_numeric_timestamp(ts_str)
        if timestamp is not None:
            return timestamp

        return self._parse_iso_timestamp(ts_str)

    def _try_parse_numeric_timestamp(self, ts_str: str) -> float | None:
        """
        Try to parse timestamp as a numeric value.
        Returns None if parsing fails.
        """
        try:
            return float(ts_str)
        except (ValueError, TypeError):
            return None


    def _parse_iso_timestamp(self, ts_str: str) -> float:
        """
        Parse timestamp from ISO 8601 date string.
        Raises ValueError if parsing fails.
        """
        try:
            dt = dateutil.parser.parse(ts_str)
            return dt.timestamp()
        except (ValueError, dateutil.parser.ParserError):
            raise ValueError(
                f"Input '{ts_str}' is neither a valid float nor a valid ISO 8601 date"
            )

    def _parse_value(self, value_str: str) -> float | str | bool | dict | list:
        """
        Parse string value into the appropriate Python type.
        Tries: boolean → JSON → number → string (in that order).
        """
        # Return non-strings as-is
        if not isinstance(value_str, str):
            return value_str

        # Return empty strings as-is
        stripped_value = value_str.strip()
        if not stripped_value:
            return stripped_value

        # Try boolean
        parsed_boolean = self._try_parse_boolean(stripped_value)
        if parsed_boolean is not None:
            return parsed_boolean

        # Try JSON (objects, arrays)
        parsed_json = self._try_parse_json(stripped_value)
        if parsed_json is not None:
            return parsed_json

        # Try number
        parsed_number = self._try_parse_number(stripped_value)
        if parsed_number is not None:
            return parsed_number

        # Default to string
        return stripped_value
    

    def _try_parse_boolean(self, value: str) -> bool | None:
        """
        Try to parse value as a boolean (case-insensitive).
        Returns None if not a boolean.
        """
        lower_value = value.lower()

        if lower_value == "true":
            return True
        if lower_value == "false":
            return False

        return None

    def _try_parse_json(self, value: str) -> dict | list | None:
        """
        Try to parse value as JSON (objects or arrays).
        Returns None if not valid JSON or if it's just a string.
        """
        try:
            parsed = json.loads(value)

            if isinstance(parsed, str):
                return None

            return parsed

        except (json.JSONDecodeError, ValueError):
            return None

    def _try_parse_number(self, value: str) -> int | float | None:
        """
        Try to parse value as a number (int or float).
        Returns None if not a valid number.
        """
        try:
            num = float(value)
            return int(num) if num.is_integer() else num
        except ValueError:
            return None
    
    def get_file_extension(self):
        return "dataframe"

    def _clean_attribute_name(self, attr_name: str) -> str:
        """Remove quotes and extra whitespace from attribute name."""
        return attr_name.strip('"').strip()