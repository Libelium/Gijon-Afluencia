from enum import Enum
from pydantic import BaseModel

class MeasureValueType(str, Enum):
    DOUBLE = "DOUBLE"
    BIGINT = "BIGINT"
    VARCHAR = "VARCHAR"
    BOOLEAN = "BOOLEAN"
    TIMESTAMP = "TIMESTAMP"
    MULTI = "MULTI"


class BaseRecord(BaseModel):
    MeasureName: str
    MeasureValueType: MeasureValueType
    MeasureValue: str
    Time: str


class Dimension(BaseModel):
    Name: str
    Value: str


Dimensions = list[Dimension]


def get_measure_value_type(value) -> MeasureValueType:

    # the order of the following checks is important, be careful when changing it
    if type(value) == int or type(value) == float:
        return MeasureValueType.DOUBLE

    elif type(value) == bool:
        return MeasureValueType.BOOLEAN

    elif isinstance(value, str):
        # try to convert the string to the most specific type possible
        try:
            value = float(value)
            return MeasureValueType.DOUBLE

        except ValueError:
            if value.lower() in ["true", "false"]:
                return MeasureValueType.BOOLEAN

    return MeasureValueType.VARCHAR
