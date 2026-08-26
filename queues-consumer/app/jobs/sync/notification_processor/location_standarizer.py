from schemas.entity_data_notification import (
    EntityAttr,
    EntityAttrType,
    EntityDataNotification,
)
from jobs.sync.notification_processor.notification_processor import (
    NotificationProcessor,
)

from schemas.entity_data_notification import EntityDataNotification
from config.logging import appLogging as logging


class LocationStandarizer(NotificationProcessor):
    """
    This class processes notification looking for locations and
    standarizing them without needing to update it on FIWARE
    """

    LATITUDE_ATTRS = ["latitudeLocation", "latitude", "r_eg25lat", "rw_dho_latitude"]
    LONGITUDE_ATTRS = ["longitudeLocation", "longitude", "r_eg25lon", "rw_dho_longitude"]
    LOCATION_ATTR = "location"

    def __get_lat_lon_loc(self, notification: EntityDataNotification):
        """
        Returns the latitude, longitude and location attributes from the
        notification data. See LATITUDE_ATTRS, LONGITUDE_ATTRS and LOCATION_ATTR
        for the names of the attributes that are going to be searched.

        returns (latitude_attr, longitude_attr, location_attr)
        """
        latitude_attr = None
        longitude_attr = None
        location_attr = None

        for attr in notification.data:

            if attr.name == LocationStandarizer.LOCATION_ATTR:
                location_attr = attr

            elif attr.name in LocationStandarizer.LATITUDE_ATTRS:
                if latitude_attr is not None:
                    logging.warning(
                        f"Multiple latitude attributes found for entity {notification.urn}, using most recent one"
                    )

                    if latitude_attr.timestamp > attr.timestamp:
                        continue

                latitude_attr = attr

            elif attr.name in LocationStandarizer.LONGITUDE_ATTRS:
                if longitude_attr is not None:
                    logging.warning(
                        f"Multiple longitude attributes found for entity {notification.urn}, using most recent one"
                    )

                    if longitude_attr.timestamp > attr.timestamp:
                        continue

                longitude_attr = attr

        return latitude_attr, longitude_attr, location_attr

    def __init__(self):
        pass

    def process(
        self, notification: EntityDataNotification
    ) -> EntityDataNotification:
        """
        Changes the location attribute (geo:json) if the entity has some latitude and longitude
        attributes that have to be propaged to the location attribute. If there are not
        such attributes, or the location is already the same as the new one, nothing is done.
        Check LATITUDE_ATTRS, LONGITUDE_ATTRS and LOCATION_ATTR for the names of the attributes
        that are going to be searched.
        """
        latitude_attr, longitude_attr, location_attr = self.__get_lat_lon_loc(
            notification
        )

        if latitude_attr is None and longitude_attr is None:
            return notification

        elif latitude_attr is None or longitude_attr is None:
            logging.warning(
                f"Location standarization failed, missing latitude or longitude attribute for entity {notification.urn}"
            )
            return notification

        new_location = {
            "type": "Point",
            "coordinates": [longitude_attr.value, latitude_attr.value],
        }

        latest_latlon_ts = max(latitude_attr.timestamp, longitude_attr.timestamp)

        # no timestamp check because the attributes must always match
        if location_attr and new_location == location_attr.value:
            return notification

        # If the location already exists and the new data is more recent, update it
        if location_attr:
            if latest_latlon_ts > location_attr.timestamp:
                location_attr.value = new_location
                location_attr.timestamp = latest_latlon_ts

        # If location_attr does not exist, add a new attribute
        else:
            notification.data.append(
                EntityAttr(
                    name=LocationStandarizer.LOCATION_ATTR,
                    value=new_location,
                    type=EntityAttrType.PROPERTY,
                    timestamp=latest_latlon_ts,
                )
            )

        return notification
