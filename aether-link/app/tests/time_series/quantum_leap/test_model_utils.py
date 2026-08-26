from app.core.time_series.data_sources.quantum_leap.schemas.table_schema import (
    TableSchema,
)
import pytest
from sqlalchemy import create_engine, MetaData, Table, Column, String, Integer, DateTime
from sqlalchemy.orm import Session
from app.core.time_series.data_sources.quantum_leap.models.md_ets_metadata import (
    MdEtsMetadata,
)
import app.core.time_series.data_sources.quantum_leap.models.utils as model_utils


@pytest.fixture
def engine():
    return create_engine("sqlite:///:memory:")


@pytest.fixture
def session(engine):
    return Session(engine)


product_metadata = {
    "name": ["name", "Text"],
    "size": ["size", "Text"],
    "price": ["price", "Integer"],
    "entity_id": ["id", "Text"],
    "time_index": ["time_index", "DateTime"],
    "entity_type": ["type", "Text"],
}


device_metadata = {
    "name_": ["name", "Text"],
    "size_": ["size", "Text"],
    "price_": ["price", "Integer"],
    "model_": ["model", "Text"],
    "entity_id_": ["id", "Text"],
    "time_index_": ["time_index", "DateTime"],
    "entity_type_": ["type", "Text"],
}


class TestModelUtils:

    def test_get_tables_metadata(self, engine, session):
        # create MdEtsMetadata table
        MdEtsMetadata.__table__.create(engine)

        # insert data
        data = [
            MdEtsMetadata(table_name="etproduct", entity_attrs=product_metadata),
            MdEtsMetadata(
                table_name="etdevice",
                entity_attrs=device_metadata,
            ),
        ]

        # insert data
        session.add_all(data)
        session.commit()

        # query all data
        q_data = model_utils.get_tables_metadata(session)
        for new_data in data:
            assert new_data.table_name in q_data

    @pytest.mark.parametrize(
        ("table_metadata", "attr", "expected"),
        [
            (product_metadata, "name", "name"),
            (product_metadata, "size", "size"),
            (product_metadata, "price", "price"),
            (product_metadata, "id", "entity_id"),
            (product_metadata, "time_index", "time_index"),
            (product_metadata, "type", "entity_type"),
            (product_metadata, "not_found", None),
            (device_metadata, "name", "name_"),
            (device_metadata, "size", "size_"),
            (device_metadata, "price", "price_"),
            (device_metadata, "model", "model_"),
            (device_metadata, "id", "entity_id_"),
            (device_metadata, "type", "entity_type_"),
            (device_metadata, "time_index", "time_index_"),
        ],
    )
    def test_get_attr_column(self, table_metadata: dict, attr: str, expected: str):
        assert model_utils.get_attr_column(table_metadata, attr) == expected

    @pytest.mark.parametrize(
        ("table_metadata", "column_name", "expected"),
        [
            (
                product_metadata,
                "name",
                "name",
            ),
            (
                product_metadata,
                "entity_id",
                "id",
            ),
            (
                product_metadata,
                "not_found",
                None,
            ),
            (
                device_metadata,
                "name_",
                "name",
            ),
            (
                device_metadata,
                "entity_id_",
                "id",
            ),
        ],
    )
    def test_get_column_attr(
        self, table_metadata: dict, column_name: str, expected: str
    ):
        assert model_utils.get_column_attr(table_metadata, column_name) == expected

    def test_get_table_attr_column(self, engine, session):
        product_table = Table(
            "etproduct",
            MetaData(),
            Column("name", String),
            Column("size", String),
            Column("price", Integer),
            Column("entity_id", String),
            Column("time_index", DateTime),
            Column("entity_type", String),
        )

        assert (
            model_utils.get_table_attr_column(product_table, product_metadata, "name")
            == product_table.c.name
        )

        assert (
            model_utils.get_table_attr_column(product_table, product_metadata, "size")
            == product_table.c.size
        )

        assert (
            model_utils.get_table_attr_column(product_table, product_metadata, "price")
            == product_table.c.price
        )

        assert (
            model_utils.get_table_attr_column(product_table, product_metadata, "id")
            == product_table.c.entity_id
        )

        assert (
            model_utils.get_table_attr_column(
                product_table, product_metadata, "time_index"
            )
            == product_table.c.time_index
        )

        assert (
            model_utils.get_table_attr_column(product_table, product_metadata, "type")
            == product_table.c.entity_type
        )

        assert (
            model_utils.get_table_attr_column(
                product_table, product_metadata, "not_found"
            )
            is None
        )

    @pytest.mark.parametrize(
        ("table_name", "expected_schema", "expected_name"),
        [
            (
                '"public"."etproduct"',
                "public",
                "etproduct",
            ),
            (
                "public.etproduct",
                "public",
                "etproduct",
            ),
        ],
    )
    def test_split_table_name(
        self, table_name: str, expected_schema: str, expected_name: str
    ):
        assert model_utils.split_table_name(table_name) == TableSchema(
            db_schema=expected_schema, name=expected_name
        )
