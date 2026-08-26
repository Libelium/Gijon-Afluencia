from datetime import datetime
from pydantic import BaseModel, field_validator
from typing import Optional
import isodate


class DeleteTimeSeriesOptions(BaseModel):
    """
    Options for time series query.
    """

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    query_id: Optional[str] = None
    tenant: str
    scope: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "start_date": "2020-01-01T00:00:00Z",
                    "end_date": "2020-01-01T00:03:00Z",
                    "query_id": "123",
                    "tenant": "gijon",
                    "scope": "/",
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
            # to avoid timezone problems
            return date.replace(tzinfo=None)
        except:
            pass
        # if it is duration
        try:
            return datetime.now() - isodate.parse_duration(value)
        except Exception as e:
            raise ValueError(
                f"Invalid date string: {value}. Date string must be in ISO8601 format (could be a duration string)"
            )
