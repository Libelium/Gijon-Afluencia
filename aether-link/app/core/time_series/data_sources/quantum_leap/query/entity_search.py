from typing import List, Tuple
from app.core.time_series.data_sources.quantum_leap.schemas.entity_schema import Entity
from sqlalchemy.orm import Session
from sqlalchemy import MetaData, or_, Table, and_
from sqlalchemy.engine import Engine
import app.core.time_series.data_sources.quantum_leap.quantum_leam_constants as ql_constants
import app.core.time_series.data_sources.quantum_leap.models.utils as model_utils


def filter_in_table(
    table: Table,
    table_metadata: dict,
    entities: List[Entity],
    db: Session,
) -> List[Entity]:
    """
    Returns a list with the entities that were found in this table.
    The entity tenant will not be checked, only the scope and the urn
    because the table name already contains the tenant.
    """

    # we should use the table metadata to get the actual name of the columns,
    # so it will be easier to migrate to NGSI-LD in the future
    id_column = model_utils.get_attr_column(
        table_metadata=table_metadata, ngsi_attr=ql_constants.ID_ATTR
    )
    id_attr = getattr(table.c, id_column)
    scope_attr = getattr(table.c, ql_constants.SCOPE_COLUMN)

    query = db.query(
        scope_attr,
        id_attr,
    )

    conditions = []
    for entity in entities:
        conditions.append(
            and_(
                scope_attr == entity.scope,
                id_attr == entity.urn,
            )
        )

    if conditions:
        query = query.filter(or_(*conditions))

    result = query.all()

    found_entities = [
        entity for entity in entities if (entity.scope, entity.urn) in result
    ]

    return found_entities
