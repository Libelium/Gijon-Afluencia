from typing import List, Optional, Any
from pydantic import BaseModel, ConfigDict
from enum import Enum


class TrasportTypes(str, Enum):
    MQTT = ("MQTT",)
    HTTP = "HTTP"


class DeviceDef(BaseModel):
    device_id: str
    apikey: str
    transport: TrasportTypes
    entity_name: Optional[str] = None
    entity_type: Optional[str] = None
    attributes: Optional[List[dict]] = None
    static_attributes: Optional[List[dict]] = None
    commands: Optional[List[dict]] = None
    endpoint: Optional[str] = None


class DeviceProvisionPayload(BaseModel):
    """
    Payload required to provision a new device
    """

    devices: List[DeviceDef]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "devices": [
                        {
                            "device_id": "Device005",
                            "apikey": "p1s3device",
                            "transport": "HTTP",
                            "endpoint": "http://fiware-manager:8000/api/v1/notify/command/Device005",
                            "attributes": [
                                {
                                    "object_id": "attr_1_s3",
                                    "name": "attr_1_s3",
                                    "type": "Property",
                                    "metadata": {
                                        "unitCode": {"type": "Text", "value": "h"}
                                    },
                                }
                            ],
                            "commands": [
                                {"name": "cmd_1", "type": "Property"},
                                {"name": "cmd_2", "type": "Property"},
                            ],
                            "static_attributes": [
                                {
                                    "name": "commands",
                                    "type": "Property",
                                    "value": ["cmd_1", "cmd_2"],
                                }
                            ],
                        }
                    ]
                }
            ]
        }
    }


class ServiceDef(BaseModel):
    apikey: str
    entity_type: str
    resource: str
    transport: TrasportTypes
    internal_attributes: Optional[Any] = None

    model_config = ConfigDict(extra='allow')


class ServiceProvisionPayload(BaseModel):
    services: List[ServiceDef]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "services": [
                        {
                            "apikey": "apikey_example",
                            "entity_type": "Device",
                            "resource": "/iot/json",
                            "transport": "HTTP",
                        }
                    ]
                }
            ]
        }
    }
