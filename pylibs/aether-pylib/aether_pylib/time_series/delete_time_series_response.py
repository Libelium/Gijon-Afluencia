from pydantic import BaseModel
from typing import List, Optional
from aether_pylib.time_series.deleted_time_series import DeletedTimeSeries
from aether_pylib.time_series.delete_time_series_options import (
    DeleteTimeSeriesOptions,
)


class DeleteTimeSeriesResponse(BaseModel):
    deleted_time_series: List[DeletedTimeSeries]
    options: Optional[DeleteTimeSeriesOptions]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "deleted_time_series": [
                        {
                            "entity_id": "urn:ngsi-ld:Building:001",
                            "attribute_id": "urn:ngsi-ld:Building:001:temperature",
                        }
                    ],
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
