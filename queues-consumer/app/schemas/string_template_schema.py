from enum import Enum
from typing import List, Optional
from pydantic import BaseModel


class StringTemplateItemType(str, Enum):
    """
    This is the type of a string template item.
    """

    STRING = "string"
    VARIABLE = "variable"


class StringCasing(str, Enum):
    """
    This is the type of a string template item.
    """

    LOWER = "lower"
    UPPER = "upper"
    NONE = "none"


class StringTemplateItem(BaseModel):
    """
    This represents an item in a string template,
    which can be a string or a variable.
    """

    type: StringTemplateItemType
    value: str
    casing: Optional[StringCasing] = None


class StringTemplate(BaseModel):
    """
    This represents a string template,
    which is an ordered concatenation of strings and variables.
    """

    items: List[StringTemplateItem]
