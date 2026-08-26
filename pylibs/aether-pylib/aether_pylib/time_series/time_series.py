from typing import List, Optional, Union
from pydantic import BaseModel
from datetime import datetime


class TimeSeriesValue(BaseModel):
    timestamp: datetime
    value: Optional[Union[int, float, bool, str, dict, list]]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "timestamp": "2020-01-01T00:00:00Z",
                    "value": 1.0,
                },
                {
                    "timestamp": "2020-01-01T00:01:00Z",
                    "value": 2.0,
                },
                {
                    "timestamp": "2020-01-01T00:02:00Z",
                    "value": 3.0,
                },
                {
                    "timestamp": "2020-01-01T00:03:00Z",
                    "value": 4.0,
                },
            ]
        }
    }


class TimeSeries(BaseModel):
    device_id: str
    measure_id: str
    values: List[TimeSeriesValue]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "device_id": "urn:ngsi-ld:Building:001",
                    "measure_id": "urn:ngsi-ld:Building:001:temperature",
                    "values": [
                        {"timestamp": "2020-01-01T00:00:00Z", "value": 1.0},
                        {"timestamp": "2020-01-01T00:01:00Z", "value": 2.0},
                        {"timestamp": "2020-01-01T00:02:00Z", "value": 3.0},
                        {"timestamp": "2020-01-01T00:03:00Z", "value": 4.0},
                    ],
                }
            ]
        }
    }
