from pydantic import BaseModel, field_validator
from typing import List

from aether_pylib.time_series.delete_time_series_options import (
    DeleteTimeSeriesOptions,
)


class DeleteTimeSeriesRequest(BaseModel):
    """
    Time series request schema
    It is the public interface for all data sources (they must implement this schema)
    """

    device_ids: List[str]
    measure_ids: List[str]
    options: DeleteTimeSeriesOptions

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "device_ids": ["urn:ngsi-ld:Building:001"],
                    "measure_ids": ["temperature"],
                    "options": {
                        "start_date": "2020-01-01T00:00:00Z",
                        "end_date": "2020-01-01T00:03:00Z",
                        "query_id": "123",
                        "tenant": "gijon",
                        "scope": "/",
                    },
                }
            ]
        }
    }

    @field_validator("options", mode="after")
    def validate_device_ids(cls, value, values):
        """
        Validate that at least one device_ids is provided.
        """

        options = value
        device_ids = values.data.get("device_ids")

        has_devices = device_ids is not None and len(device_ids) > 0

        if not has_devices:
            raise ValueError(
                f"No device_ids are provided. At least one of them must be provided"
            )

        return value
