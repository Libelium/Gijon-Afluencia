from pydantic import BaseModel
from typing import List, Optional
from aether_pylib.time_series.time_series import TimeSeries
from aether_pylib.time_series.time_series_options import TimeSeriesOptions


class TimeSeriesResponse(BaseModel):
    time_series: List[TimeSeries]
    options: Optional[TimeSeriesOptions]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "time_series": [
                        {
                            "entity_id": "urn:ngsi-ld:Building:001",
                            "attribute_id": "urn:ngsi-ld:Building:001:temperature",
                            "values": [
                                {"timestamp": "2020-01-01T00:00:00Z", "value": 1.0},
                                {"timestamp": "2020-01-01T00:01:00Z", "value": 2.0},
                                {"timestamp": "2020-01-01T00:02:00Z", "value": 3.0},
                                {"timestamp": "2020-01-01T00:03:00Z", "value": 4.0},
                            ],
                        }
                    ],
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
    