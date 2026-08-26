from datetime import datetime
from enum import Enum
from typing import Any, Optional, List
from config.logging import appLogging as logging
from pydantic import BaseModel


class EntityAttrType(str, Enum):
    """
    This is the Platform data item type.
    """

    PROPERTY = "Property"
    RELATIONSHIP = "Relationship"
    COMMAND = "Command"


class CommandAttrValue(BaseModel):
    """
    This is the representation of an ngsi attribute
    in Platform.
    """

    info: Any
    status: Any
    info_timestamp: float
    status_timestamp: float

class EntityAttr(BaseModel):
    """
    This is the representation of an ngsi attribute
    in Platform.
    """

    name: str
    value: Any
    type: EntityAttrType
    units: Optional[str] = None
    timestamp: float  # float because of leap seconds
    timestamp_override: Optional[bool] = False


class EntityDataNotification(BaseModel):
    """
    This class represents the Platform entity data notification,
    received from the FIWARE context broker, for one particular
    entity.
    """

    urn: str
    tenant: str
    scope: str
    type: str
    notified_at: Optional[float] = None
    db_id: Optional[int] = None
    devices: Optional[List[int]] = None
    data: List[EntityAttr]
    recently_created: Optional[bool] = False

    def latest_timestamp(self, ignore_overriden=True) -> float:
        """
        This method returns the latest timestamp of the notification.
        It is used to determine if the notification is older than the
        current time.
        """
        if not self.data:
            return None

        timestamps = [
            attr.timestamp
            for attr in self.data
            if (not ignore_overriden or not attr.timestamp_override)
            and attr.timestamp is not None
        ]

        if not timestamps:
            return None

        return max(timestamps)
    

    def get_all_attributes(self, ignore_overriden: bool = True) -> List[EntityAttr]:
            """
            Devuelve todos los EntityAttr válidos,
            ignorando los overrides (si ignore_overriden=True)
            y excluyendo los atributos cuyo name sea 'commands'.
            Ordenados de más reciente a más antiguo según timestamp.
            """
            if not self.data:
                return []

            filtered = [
                attr for attr in self.data
                if attr.timestamp is not None
                and (not ignore_overriden or not attr.timestamp_override)
                and attr.name.lower() != 'commands'
            ]
            # Orden descendente por timestamp
            return sorted(filtered, key=lambda a: a.timestamp, reverse=True)


class DataNotification(BaseModel):
    """
    This class represents the Platform data notification,
    received from the FIWARE context broker.
    """

    notified_at: float  # float because of leap seconds
    data: List[EntityDataNotification]
