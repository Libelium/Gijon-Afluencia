from pydantic import BaseModel, field_validator, conlist
from typing import List, Optional

from aether_pylib.time_series.time_series_options import TimeSeriesOptions


class TimeSeriesRequest(BaseModel):
    """
    Time series request schema
    It is the public interface for all data sources (they must implement this schema)
    """

    device_ids: List[str]
    measure_ids: Optional[List[str]] = []
    options: TimeSeriesOptions

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "device_ids": ["urn:ngsi-ld:Building:001"],
                    "measure_ids": ["temperature"],
                    "options": {
                        "start_date": "2020-01-01T00:00:00Z",
                        "end_date": "2020-01-01T00:03:00Z",
                        "order": "asc",
                        "limit": 100,
                        "aggregation": {
                            "type": "mean",
                            "interval": "PT30S",
                        },
                    },
                }
            ]
        }
    }

    @field_validator("options", mode="after")
    def validate_device_ids(cls, value, values):
        """
        Validate that at least one of device_ids or where clause is provided.
        This is because the implementation of the where clause is not yet fully supported,
        so for now we validate the request allowing only the supported combination.
        """

        options = value
        device_ids = values.data.get("device_ids")

        has_devices = device_ids is not None and len(device_ids) > 0
        has_where = options is not None and options.where is not None

        if not has_devices and not has_where:
            raise ValueError(
                f"Neither device_ids nor where clause are provided. At least one of them must be provided"
            )

        return value
