from schemas.entity_data_notification import EntityDataNotification
from sqlalchemy.orm import Session
import models.crud.crud_devices as crud_devices
import models.crud.crud_entity_properties as crud_entity_properties
import helpers.aether_link.aether_link_helper as aether_link_helper
import models.crud.crud_entity as crud_entity
from config.logging import appLogging as logging
import json
from datetime import datetime


def sync_entities_location(
    device_data_notification: EntityDataNotification,
    db: Session,
    realtime_db: Session,
):
    """
    This method is responsible for updating the location of the related entities the device belongs to.
    """

    device_id = crud_devices.get_device_id_for_entity(
        device_data_notification.db_id, db
    )
    if not device_id:
        return

    entity_ids = crud_devices.get_entities_ids_for_device_id(device_id, db)
    urns_dict = crud_entity.get_entity_urns_for_ids(entity_ids, db)

    for attr in device_data_notification.data:
        if attr.name == "location":
            for entity_id in entity_ids:
                logging.info(f"Syncing location for entity {entity_id}")

                old_value = crud_entity_properties.get_entity_property(
                    entity_id, "location", realtime_db
                )

                if old_value is not None:
                    old_value_correct = json.loads(old_value.value.replace("'", '"'))

                    if old_value_correct == attr.value:
                        logging.info(
                            f"Location for entity {entity_id} is already {attr.value}"
                        )
                        continue

                urn_tuple = urns_dict.get(entity_id, None)

                if not urn_tuple:
                    logging.warning(f"Entity URN not found for entity {entity_id}")
                    continue

                urn, tenant, scope = urn_tuple

                attributes = {
                    "location": {
                        "type": "Property",
                        "value": attr.value,
                    }
                }

                result = aether_link_helper.update_on_context_broker(
                    urn=urn,
                    tenant=tenant,
                    scope=scope,
                    attributes=attributes,
                )

                if not result["updated"]:
                    logging.error(
                        f"Failed to update location for entity {entity_id}: {result['response']}"
                    )
                else:
                    logging.info(
                        f"Location for entity {entity_id} updated successfully"
                    )
