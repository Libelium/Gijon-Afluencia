from schemas.entity_data_notification import EntityDataNotification
from sqlalchemy.orm import Session
import models.crud.crud_devices as crud_devices
import models.crud.crud_entity as crud_entity
import models.crud.crud_device_types as crud_device_types
from config.logging import appLogging as logging


def sync_verticals(device_data_notification: EntityDataNotification, db: Session):
    """
    This method is responsible for updating the related entities according
    to the SMSP verticals reporting. It just add realted entities to the device.
    It does not remove any, because it's not an expected behavior for the SMSP.
    """
    entity = crud_entity.get_entity_by_id(device_data_notification.db_id, db)
    et = entity.datamodel

    if et == 'DeviceHealthcheck': return None

    logging.info(f"Syncing verticals for entity {device_data_notification.urn}")

    device = crud_devices.get_device_id_for_entity(device_data_notification.db_id, db)
    if device:
        return None

    serial = device_data_notification.urn.split(":")[-1].split("_")[0]
    device = crud_devices.get_device_by_serial(serial, db)
    if not device:
        return None

    dt = crud_device_types.get(device.device_type_id, db)
    if  "smsp" in dt.code:
        crud_entity.relate_entity_to_device(
            device_data_notification.db_id,
            device.id,
            None,
            db,
        )
        logging.info(f"Entity {device_data_notification.urn} related to device {device.serial}")

    return None
