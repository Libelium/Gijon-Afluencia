from typing import Tuple
from app.core.time_series.data_sources.quantum_leap.models.md_ets_metadata import (
    MdEtsMetadata,
)
from sqlalchemy import Table, MetaData, Column
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from app.core.time_series.data_sources.quantum_leap.schemas.table_schema import (
    TableSchema,
)


def get_table_model(
    table_schema: TableSchema, engine: Engine, metadata: MetaData
) -> Table:
    """
    Get the SQLAlchemy table model for the given table name
    """
    return Table(
        table_schema.name, metadata, autoload_with=engine, schema=table_schema.db_schema
    )


def get_tables_metadata(session: Session) -> dict:
    """
    Get table attr correspondences (mt_ets_metadata), a mapping to
    know how is the column named in the database and the type of the column
    """
    md_ets_metadata = session.query(MdEtsMetadata).all()

    return {metadata.table_name: metadata.entity_attrs for metadata in md_ets_metadata}


def get_attr_column(table_metadata: dict, ngsi_attr: str) -> str:
    """
    Get the column name in the database for the given ngsi attribute
    """
    return next(
        (
            key
            for key, [attr_name, _] in table_metadata.items()
            if attr_name == ngsi_attr
        ),
        None,
    )


def get_table_attr_column(
    table_model: Table,
    table_metadata: dict,
    attr: str,
) -> Column:
    """
    Returns the column object for the given attribute in the table model.
    None if the attribute is not found.
    """

    column_name = get_attr_column(table_metadata, attr)

    if column_name is None:
        return None

    return getattr(table_model.c, column_name, None)


def get_column_attr(table_metadata: dict, column_name: str) -> str:
    """
    Get the NGSI attribute name for the given column name
    """
    return next(
        (
            attr_name
            for key, [attr_name, _] in table_metadata.items()
            if key == column_name
        ),
        None,
    )


def split_table_name(table_name: str) -> TableSchema:
    """
    Split the table name in schema and table name
    "schema_name"."table_name" -> ("schema_name", "table_name")
    """
    schema, table = table_name.replace('"', "").split(".", 1)

    return TableSchema(db_schema=schema, name=table)
