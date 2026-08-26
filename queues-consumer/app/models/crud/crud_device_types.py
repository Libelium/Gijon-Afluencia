from models.device_types_model import DeviceType
from config.logging import appLogging as logging

from sqlalchemy.orm import Session


def get(id: int, db: Session) -> DeviceType | None:
    """
    Returns the device type with the given id.
    """

    query_result = db.query(DeviceType).filter(DeviceType.id == id).first()

    if not query_result:
        return None

    return query_result
