from datetime import datetime, timedelta
from pydantic import BaseModel, field_validator
from typing import List, Optional
from enum import Enum
import pandas as pd
import isodate
import re

from aether_pylib.time_series.time_scope import TimeScope


class TimeSeriesOrdering(Enum):
    """
    Time series ordering in the query. Results order will be the same,
    but if asc, the pagination will start from the end, if not, from the beginning.
    """

    ASC = "asc"
    DESC = "desc"


class TimeSeriesAggregationOptionsType(str, Enum):
    """
    Types of aggregation for time series.
    """

    MEAN = "mean"
    MOVING_AVG = "moving_avg"
    SUM = "sum"
    MIN = "min"
    MAX = "max"
    PERCENTILE = "percentile"


class TimeSeriesAggregationOptions(BaseModel):
    """
    Aggregation options for time series.
    """

    type: str
    interval: timedelta

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": "mean",
                    "interval": "PT30S",
                },
                {
                    "type": "sum",
                    "interval": "PT3M",
                },
            ]
        }
    }

    @field_validator("type", mode="before")
    def validate_type(cls, value):
        types = [t.value for t in TimeSeriesAggregationOptionsType]
        if isinstance(value, str):
            if value in types and value != "percentile":
                return value

            elif re.match(r"^[a-z]+-\d+$", value):
                func, num = value.split("-")
                if func in types and num.isdigit():
                    return value

                raise ValueError(
                    f"Invalid type value: {value}, percentile should be like 'percentile-N', 0 <= N <= 100"
                )

            raise ValueError(f"Invalid type value: {value}")
        raise ValueError(f"Invalid type value: {value}")

    @field_validator("interval", mode="before")
    def parse_relative_duration_str(cls, value):
        try:
            delta = pd.to_timedelta(value)
            if delta == pd.Timedelta(0):
                raise ValueError(
                    "Invalid interval string: {value}. Interval string must be in ISO8601 format (duration string). Years and months are not allowed"
                )

            return delta

        except Exception as e:
            print(e)
            raise ValueError(
                "Invalid interval string: {value}. Interval string must be in ISO8601 format (duration string). Years and months are not allowed"
            )


class WhereClauseOperator(Enum):
    """
    Operators for where clause.
    For now, only eq is supported.
    """

    EQ = "="


class WhereClauseOperation(Enum):
    AND = "AND"


class WhereClause(BaseModel):
    conditions: List[List[str | float | int | bool]]
    operation: WhereClauseOperation = WhereClauseOperation.AND

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "conditions": [["field1", "=", 1], ["field2", "=", "2"]],
                    "operation": "AND",
                }
            ]
        }
    }

    @field_validator("conditions", mode="before")
    def validate_conditions(cls, value):
        if len(value) == 0:
            raise ValueError(
                f"Invalid conditions: {value}. Conditions must not be empty"
            )

        if len(value) > 1:
            raise ValueError(
                f"Invalid conditions: {value}. Only one condition is supported"
            )

        # only equal operator is supported
        for condition in value:
            if condition[1] != WhereClauseOperator.EQ.value:
                raise ValueError(
                    f"Invalid operator: {condition[1]}. Only equal operator is supported"
                )

        return value


class TimeSeriesOptions(BaseModel):
    """
    Options for time series query.
    """

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    order: Optional[TimeSeriesOrdering] = None
    limit: Optional[int] = 100
    aggregation: Optional[TimeSeriesAggregationOptions] = None
    period: Optional[List[TimeScope]] = None
    query_id: Optional[str] = None
    where: Optional[WhereClause] = None
    tenant: str
    scope: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "start_date": "2020-01-01T00:00:00Z",
                    "end_date": "2020-01-01T00:03:00Z",
                    "order": "asc",
                    "limit": 100,
                    "aggregation": {
                        "type": "mean",
                        "interval": "PT30S",
                    },
                    "period": [
                        {
                            "months": [0, 1, 2, 3],
                            "month_days": [],
                            "week_days": [0, 1, 2, 3, 4],
                            "hours": [["12:00:00", "15:00:00"]],
                            "exclude": [
                                {
                                    "year": 2020,
                                    "month": 0,
                                    "month_day": 1,
                                },
                                {
                                    "year": 2020,
                                    "month": 3,
                                    "month_day": 2,
                                },
                            ],
                        }
                    ],
                    "query_id": "123",
                    "where": [["field1", "eq", 1], ["field2", "eq", "2"]],
                }
            ]
        }
    }

    @field_validator("start_date", "end_date", mode="before")
    def parse_relative_duration_str(cls, value):
        # value is a str in ISO8601 format
        # if it is isodate
        if value is None:
            return None

        # if it is already a datetime
        if isinstance(value, datetime):
            return value

        try:
            date = isodate.parse_datetime(value)
            return date
        except:
            pass
        # if it is duration
        try:
            return datetime.now() - isodate.parse_duration(value)
        except Exception as e:
            raise ValueError(
                "Invalid date string: {value}. Date string must be in ISO8601 format (could be a duration string)"
            )

    @field_validator("limit", mode="before")
    def validate_limit(cls, value):
        if value < 1:
            raise ValueError("Invalid limit: {value}. Limit must be greater than 0")

        if value is None:
            return 100

        return value
