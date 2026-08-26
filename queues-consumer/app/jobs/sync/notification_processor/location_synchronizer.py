import json
from datetime import datetime
from typing import Any, Dict

import models.crud.crud_devices as crud_devices
from config.logging import appLogging as logging
from jobs.sync.notification_processor.notification_processor import (
    NotificationProcessor,
)
from models.entity_properties_model import EntityProperty, MeasureType
from schemas.entity_data_notification import (
    EntityAttr,
    EntityAttrType,
    EntityDataNotification,
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from tasks.sync import save_timeseries_job
from utils.ngsi import ngsi_ld_utils


class LocationSynchronizer(NotificationProcessor):
    """
    This processor synchronizes the location of an entity with the device
    related entities
    """

    def __init__(self, main_db: Session, realtime_db: Session):
        self.main_db = main_db
        self.realtime_db = realtime_db

    def __get_latest_location(self, locations: Dict[str, Dict[str, Any]]) -> Dict:
        """
        locations dict is the one returned by crud_devices.get_related_entities_attrs.
        It returns the attribute in locations with the most recent timestamp. Check
        crud_devices.get_related_entities_attrs for more information.
        """
        latest = None

        for entity_id, attrs in locations.items():
            location = attrs.get("location")

            if location is None:
                continue

            timestamp = location.get("timestamp")

            if timestamp is None:
                continue

            if latest is None or timestamp > latest["timestamp"]:
                latest = location

        return latest

    def __get_notification_location(
        self, notification: EntityDataNotification
    ) -> EntityAttr:
        """
        Returns the location attribute from the notification data,
        in a format compatible with the locations dict returned by
        crud_devices.get_related_entities
        """
        for attr in notification.data:
            if attr.name == "location":
                return attr

        return None

    def __sync_location_to_ts_database(
        self, entity_id: str, attrs: Dict[str, Any], latest_location: Dict
    ) -> None:
        """
        Sync location update to database for a given entity.
        """
        try:
            # Extract entity type from URN
            entity_type = ngsi_ld_utils.get_entity_type_from_urn(attrs["urn"])

            # Create a synthetic notification for this entity with the location attribute
            notification = EntityDataNotification(
                urn=attrs["urn"],
                tenant=attrs["tenant"],
                scope=attrs["scope"],
                type=entity_type,
                db_id=entity_id,
                data=[
                    EntityAttr(
                        name="location",
                        value=latest_location["value"],
                        type=EntityAttrType.PROPERTY,
                        timestamp=latest_location["timestamp"].timestamp(),
                        units=None,
                    )
                ],
            )

            logging.info(f"Saving location to TimescaleDB for entity {entity_id} ({entity_type})")
            save_timeseries_job(notification)

        except Exception as e:
            logging.error(
                f"Failed to save location to TimescaleDB for entity {entity_id}: {e}"
            )

    def __sync_entity_locations(
        self,
        locations: Dict[str, Dict[str, Any]],
        latest_location: Dict,
    ):
        """
        Updates all the entity locations with the latest location. This is done
        in the realtime entity properties table. The location is only updated if
        it was changed.
        """

        bulk_inserts = []
        bulk_updates = []

        location_value_str = json.dumps(latest_location["value"]).replace('"', "'")
        now = datetime.now()

        for entity_id, attrs in locations.items():
            location = attrs.get("location")

            if location:

                if location["value"] == latest_location["value"]:
                    continue

                bulk_updates.append(
                    {
                        "id": location["id"],
                        "value": location_value_str,
                        "timestamp": latest_location["timestamp"],
                        "updated_at": now,
                    }
                )

            else:
                bulk_inserts.append(
                    EntityProperty(
                        urn=attrs["urn"],
                        tenant=attrs["tenant"],
                        scope=attrs["scope"],
                        entity_id=entity_id,
                        name="location",
                        value=location_value_str,
                        value_type=latest_location["value_type"],
                        timestamp=latest_location["timestamp"],
                        units=None,
                        created_at=now,
                        updated_at=now,
                    )
                )
            
            self.__sync_location_to_ts_database(entity_id, attrs, latest_location)
        
        logging.info(f"Location has been synced for entity: {locations.keys()}, with location {latest_location['value'] if latest_location else None} ")
        
        if bulk_inserts:
            self.realtime_db.add_all(bulk_inserts)

        if bulk_updates:
            self.realtime_db.bulk_update_mappings(
                EntityProperty,
                bulk_updates,
            )

        if bulk_inserts or bulk_updates:
            self.realtime_db.commit()

    def __update_notification_location(
        self,
        locations: Dict[str, Dict[str, Any]],
        notification: EntityDataNotification,
    ) -> Dict:
        """
        Returns the latest location from the locations dict and the notification.
        If the notification location is outdated, it updates the notification location
        the latest location, even when the notification has no location attr.

        locations must not contain the notification entity, and all the attributes must
        be of the correrct type (location must be a dict, although it is stored as a string in the db)
        """
        this_location = self.__get_notification_location(notification)
        latest_location = self.__get_latest_location(locations)

        if not this_location and not latest_location:
            return None

        if not this_location:
            logging.info(
                f"Updating notification for entity {notification.db_id} with latest location: {latest_location}"
            )
            notification.data.append(
                EntityAttr(
                    name="location",
                    value=latest_location["value"],
                    type=EntityAttrType.PROPERTY,
                    timestamp=latest_location["timestamp"].timestamp(),
                )
            )

        elif (
            not latest_location
            or this_location.timestamp >= latest_location["timestamp"].timestamp()
        ):
            latest_location = {
                "value": this_location.value,
                "value_type": MeasureType.STRING.value,
                "timestamp": datetime.fromtimestamp(this_location.timestamp),
            }

        else:
            this_location.value = latest_location["value"]
            this_location.timestamp = latest_location["timestamp"].timestamp()

        return latest_location

    def process(
        self, notification: EntityDataNotification
    ) -> EntityDataNotification:
        """
        This method processes a location notification.
        """

        locations = crud_devices.get_related_entities_attrs(
            notification.devices,
            ["location"],
            self.main_db,
            self.realtime_db,
        )

        if notification.db_id in locations:
            # ignore this notification entity, because we already have the notification
            del locations[notification.db_id]

        if not locations:
            return notification

        # transform locations to dict (they are stored as strings in the db)
        for _, attrs in locations.items():
            location = attrs.get("location")

            if location:
                location["value"] = json.loads(location["value"].replace("'", '"'))

        latest_location = self.__update_notification_location(locations, notification)

        if latest_location:
            self.__sync_entity_locations(locations, latest_location)

        return notification
