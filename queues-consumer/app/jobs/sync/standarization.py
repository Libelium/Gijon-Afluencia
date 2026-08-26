"""
This module is reposible of standarizing the data from fiware into new
attributes that are going to be used in the application.
"""

from schemas.entity_data_notification import EntityDataNotification
from config.logging import appLogging as logging
import helpers.aether_link.aether_link_helper as aether_link_helper

LATITUDE_ATTRS = ["latitudeLocation", "latitude", "r_eg25lat"]
LONGITUDE_ATTRS = ["longitudeLocation", "longitude", "r_eg25lon"]
LOCATION_ATTR = "location"


def __get_lat_lon_loc(notification: EntityDataNotification):
    """
    Returns the latitude, longitude and location attributes from the
    notification data. See LATITUDE_ATTRS, LONGITUDE_ATTRS and LOCATION_ATTR
    for the names of the attributes that are going to be searched.

    returrns (latitude_attr, longitude_attr, location_attr)
    """
    latitude_attr = None
    longitude_attr = None
    location_attr = None

    for attr in notification.data:

        if attr.name == LOCATION_ATTR:
            location_attr = attr

        elif attr.name in LATITUDE_ATTRS:
            if latitude_attr is not None:
                logging.warning(
                    f"Multiple latitude attributes found for entity {notification.urn}, using most recent one"
                )

                if latitude_attr.timestamp > attr.timestamp:
                    continue

            latitude_attr = attr

        elif attr.name in LONGITUDE_ATTRS:
            if longitude_attr is not None:
                logging.warning(
                    f"Multiple longitude attributes found for entity {notification.urn}, using most recent one"
                )

                if longitude_attr.timestamp > attr.timestamp:
                    continue

            longitude_attr = attr

    return latitude_attr, longitude_attr, location_attr


def get_new_location(notification: EntityDataNotification):
    """
    Returns a new location geo:json if the entity has some latitude and longitude
    attributes that have to be propaged to the location attribute. If there are not
    such attributes, or the location is already the same as the new one, returns None.
    Check LATITUDE_ATTRS, LONGITUDE_ATTRS and LOCATION_ATTR for the names of the attributes
    that are going to be searched.
    """
    latitude_attr, longitude_attr, location_attr = __get_lat_lon_loc(notification)

    if latitude_attr is None and longitude_attr is None:
        return None

    elif latitude_attr is None or longitude_attr is None:
        logging.warning(
            f"Location standarization failed, missing latitude or longitude attribute for entity {notification.urn}"
        )
        return None

    new_location = {
        "type": "Point",
        "coordinates": [longitude_attr.value, latitude_attr.value],
    }

    # no timestamp check because the attributes must always match
    if location_attr and new_location == location_attr.value:
        return None

    return new_location


def location_standarization(notification: EntityDataNotification):
    """
    Some devices might send the location in different formats, for example,
    smart spot sends location in two attributes: latitudeLocation and
    longitudeLocation.

    This method is responsible of standarizing the location into a single
    attribute called location, which is a GeoJson point
    {
        "type": "Point",
        "coordinates": [longitude, latitude]
    }

    IMPORTANT: The changes are sent to the context broker only if the location is
    different from the one that is already stored in the context broker, if not,
    notification loops will be created.
    """

    new_location = get_new_location(notification)

    if new_location is None:
        return

    # change the value in the context broker
    change_result = aether_link_helper.update_on_context_broker(
        notification.urn,
        notification.tenant,
        notification.scope,
        {"location": {"value": new_location, "type": "Property"}},
    )

    if not change_result["updated"]:
        logging.error(
            f"Failed to update location for entity {notification.urn}: {change_result['response']} (standarization failed)"
        )
    else:
        logging.info(f"Location for entity {notification.urn} successfully standarized")
