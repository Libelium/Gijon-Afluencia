import io
import pandas as pd
import pytest
from jobs.data.data_importation.parser.xlsx_parser import XlsxParser
from schemas.data_importation_request import DataImportationRequest
from schemas.entity_data_notification import (
    EntityAttr,
    EntityAttrType,
    EntityDataNotification,
)


# ==============================================================================
# FIXTURES Y HELPERS
# ==============================================================================

@pytest.fixture
def parser():
    return XlsxParser()


@pytest.fixture
def request_factory():
    def _factory(
        tenant="default_tenant", scope="/", user_id=1
    ):
        return DataImportationRequest(
            user_id=user_id,
            tenant=tenant,
            scope=scope,
            storage_file_path="test.xlsx",
        )
    return _factory


def df_to_xlsx(df: pd.DataFrame) -> io.BytesIO:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    return buffer


# ==============================================================================
# TESTS
# ==============================================================================

class TestXlsxBasic:
    """Validación básica de parsing XLSX"""

    def test_parse_single_row_multi_attributes(self, parser, request_factory):
        df = pd.DataFrame({
            "timestamp": ["1750280400"],
            "urn": ["urn:ngsi-ld:Device:1"],
            "type": ["Device"],
            "temperature": ["25.5"],
            "humidity": ["60"],
        })
        buffer = df_to_xlsx(df)
        request = request_factory(tenant="t1", scope="/")

        notifications = parser.parse(buffer, request)
        assert len(notifications) == 1
        assert len(notifications[0].data) == 2


class TestValueTypes:
    """Verifica conversión de valores como en CSV"""

    @pytest.mark.parametrize(
        "data,attr_name,expected",
        [
            ({"timestamp": ["1750"], "urn": ["urn:ngsi-ld:Device:1"], "type": ["Device"], "val": ["10"]}, "val", 10),
            ({"timestamp": ["1750"], "urn": ["urn:ngsi-ld:Device:1"], "type": ["Device"], "val": ["20.5"]}, "val", 20.5),
            ({"timestamp": ["1750"], "urn": ["urn:ngsi-ld:Device:1"], "type": ["Device"], "val": ["true"]}, "val", True),
            ({"timestamp": ["1750"], "urn": ["urn:ngsi-ld:Device:1"], "type": ["Device"], "val": ['{"a":1}']}, "val", {"a": 1}),
            ({"timestamp": ["1750"], "urn": ["urn:ngsi-ld:Device:1"], "type": ["Device"], "name": ["Device 1"]}, "name", "Device 1"),
        ],
    )
    def test_value_parsing(self, parser, request_factory, data, attr_name, expected):
        df = pd.DataFrame(data)
        buffer = df_to_xlsx(df)
        request = request_factory(tenant="t1")

        notifications = parser.parse(buffer, request)

        attr = next(a for a in notifications[0].data if a.name == attr_name)
        assert attr.value == expected


class TestMultipleEntities:
    """Agrupación por múltiples entidades"""

    def test_multiple_entities(self, parser, request_factory):
        df = pd.DataFrame({
            "timestamp": ["1750", "1751", "1752"],
            "urn": ["urn:ngsi-ld:Device:A", "urn:ngsi-ld:Device:B", "urn:ngsi-ld:Device:A"],
            "type": ["Device", "Device", "Device"],
            "value": ["10", "20", "30"],
        })
        buffer = df_to_xlsx(df)
        request = request_factory()

        notifications = parser.parse(buffer, request)
        assert len(notifications) == 2


class TestMetadataPriority:
    """XLSX metadata tenant/scope takes priority over request values. URN and type always from file."""

    def test_request_metadata_overrides_file(self, parser, request_factory):
        df = pd.DataFrame({
            "timestamp": ["1750"],
            "urn": ["urn:ngsi-ld:CSVType:001"],
            "type": ["CSVType"],
            "tenant": ["csv_t"],
            "scope": ["/csv"],
            "value": ["10"],
        })
        buffer = df_to_xlsx(df)

        request = request_factory(
            tenant="REQ_TENANT", scope="/REQ"
        )

        notifications = parser.parse(buffer, request)
        entity = notifications[0]

        assert entity.urn == "urn:ngsi-ld:CSVType:001"
        assert entity.tenant == "REQ_TENANT"
        assert entity.scope == "/REQ"
        assert entity.type == "CSVType"


class TestErrorHandling:
    """Validación de errores como CSV"""

    def test_missing_timestamp(self, parser, request_factory):
        df = pd.DataFrame({"urn": ["urn:ngsi-ld:Device:1"], "type": ["Device"], "value": ["10"]})
        buffer = df_to_xlsx(df)

        request = request_factory()
        with pytest.raises(ValueError):
            parser.parse(buffer, request)

    def test_empty_dataframe_raises(self, parser, request_factory):
        df = pd.DataFrame(columns=["timestamp"])
        buffer = df_to_xlsx(df)

        request = request_factory()
        with pytest.raises(ValueError):
            parser.parse(buffer, request)


class TestDataIntegrity:
    def test_attribute_order_preserved(self, parser, request_factory):
        df = pd.DataFrame({
            "timestamp": ["1750"],
            "urn": ["urn:ngsi-ld:Device:1"],
            "type": ["Device"],
            "a": ["1"],
            "b": ["2"],
            "c": ["3"],
        })
        buffer = df_to_xlsx(df)

        request = request_factory()
        notifications = parser.parse(buffer, request)

        names = [a.name for a in notifications[0].data]
        assert names == ["a", "b", "c"]
