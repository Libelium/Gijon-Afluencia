import logging
from datetime import datetime
from sqlalchemy.orm import Session
from models.crud.crud_log import create_error_log, create_info_log
from schemas.entity_data_notification import EntityDataNotification
from schemas.resource_schema import ResourceType
import models.crud.crud_devices as crud_devices
import models.crud.crud_entity_properties as crud_entity_properties

ERROR_ATTRS = ["r_errors"]


def sync_errors(
    entity_data_notification: EntityDataNotification,
    db: Session,
    realtime_db: Session,
):
    """
    This method is responsible for updating the errors of the device that the entity belongs to.
    """
    if not entity_data_notification.devices:
        return

    for attr in entity_data_notification.data:

        if attr.name not in ERROR_ATTRS:
            continue

        # get the realtime latest error attr for this entity
        latest_error_attr = crud_entity_properties.get_entity_property(
            entity_data_notification.db_id, attr.name, realtime_db
        )

        attr_timestamp = datetime.fromtimestamp(attr.timestamp)

        if (
            latest_error_attr is not None
            and latest_error_attr.timestamp >= attr_timestamp
        ):
            # already have the latest error logged, do not log this error
            continue

        for device in crud_devices.get_devices(entity_data_notification.devices, db):

            create_error_log(
                db,
                {
                    "datetime": attr_timestamp,
                    "created_at": datetime.now(),
                    "updated_at": datetime.now(),
                    "message": f"Error in device {device.name} ({device.serial})",
                    "extra": {
                        "serial": device.serial,
                        "case_id": device.case_id,
                        "error": str(attr.value),
                    },
                    "resource_type": ResourceType.DEVICES,
                    "resource_id": device.id,
                },
            )
