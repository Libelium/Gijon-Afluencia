from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class TimeSeriesHashResponse(BaseModel):
    """
    Response schema for the timeseries hash endpoint.

    Computed inside the database via a deterministic
    digest('sha256', string_agg(... ORDER BY ...)) over the canonical row
    representation. Calling the endpoint twice without underlying writes
    yields an identical data_hash.
    """

    tenant: str
    scope: Optional[str] = None
    entity_ids: List[str]
    measure_ids: List[str]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    row_count: int
    algorithm: str = "sha256"
    data_hash: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "tenant": "demo",
                    "scope": "/",
                    "entity_ids": ["urn:ngsi-ld:Building:001"],
                    "measure_ids": ["temperature"],
                    "start_date": "2026-04-01T00:00:00Z",
                    "end_date": "2026-04-29T00:00:00Z",
                    "row_count": 12345,
                    "algorithm": "sha256",
                    "data_hash":
                        "9b74c9897bac770ffc029102a200c5de4dc0b29b9eb40b36e7a68f5ec57a2eaa",
                }
            ]
        }
    }
