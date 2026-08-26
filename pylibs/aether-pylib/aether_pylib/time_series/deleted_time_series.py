from pydantic import BaseModel


class DeletedTimeSeries(BaseModel):
    device_id: str
    measure_id: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "device_id": "urn:ngsi-ld:Building:001",
                    "measure_id": "urn:ngsi-ld:Building:001:temperature",
                }
            ]
        }
    }
