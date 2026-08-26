from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel


class MappingSchemaType(str, Enum):
    """
    Types of mapping schema,
    only table is supported for now.
    """

    TABLE = "Table"


class MappingSchema(BaseModel):
    """
    This is the representation of a mapping schema in Platform.
    """

    type: MappingSchemaType
    mapping: Any
    variables: Optional[List[str]] = []
