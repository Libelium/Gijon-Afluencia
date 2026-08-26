from sqlalchemy import Boolean, Column, Integer, String, Text, MetaData, Table
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION, JSONB, TIMESTAMP


def build_entity_data_model(metadata: MetaData, schema: str) -> Table:
    """
    Build the entity_data table model. This is needed for
    dynamic schema mapping.
    """
    table = metadata.tables.get(f"{schema}.entity_data", None)

    if table is not None:
        return table

    return Table(
        "entity_data",
        metadata,
        Column("time", TIMESTAMP(timezone=True), nullable=False),
        Column("entity_id", String(256), nullable=False),
        Column("entity_type", String(256), nullable=False),
        Column("attr_id", String(64), nullable=False),
        Column("scope_id", String(256), nullable=False),
        Column("attr_value_type", String(32)),
        Column("attr_double_value", DOUBLE_PRECISION, nullable=True),
        Column("attr_string_value", Text, nullable=True),
        Column("attr_boolean_value", Boolean, nullable=True),
        Column("attr_json_value", JSONB(none_as_null=True), nullable=True),
        schema=schema,
        # just in case the table already exists
        # (should not happen because of the check above)
        extend_existing=True,
    )
