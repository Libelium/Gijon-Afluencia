from typing import Optional
from sqlalchemy.orm import Session
from config.logging import appLogging as logging
from models.mapping_schema_model import MappingSchema


def get_mapping_schema(db: Session, schema_id: int) -> Optional[MappingSchema]:
    """Devuelve una MappingSchema o None si no existe."""
    return db.query(MappingSchema).get(schema_id)
