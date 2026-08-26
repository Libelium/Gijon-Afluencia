from datetime import datetime
from typing import Any, Dict, Optional, TypedDict, List
from config.logging import appLogging as logging
from pydantic import BaseModel
from schemas.entity_data_notification import EntityAttrType


def non_attribute_keys() -> List[str]:
    return [
        "id",
        "type",
        "@context",
        "createdAt",
        "modifiedAt",
        "observedAt",
        "deletedAt",
    ]


def is_system_attribute(attr_key: str) -> bool:
    return attr_key in non_attribute_keys()


def is_command_info(attr_key: str, attr_value: str | dict, attr_type: str):
    """
    The attribute is a command info if it is like "command_info" and
    the value:
    "value": {
    "@type": "commandResult",
    "@value": SOME_VALUE
    }
    """

    return (
        attr_type == "Property"
        and attr_key.endswith("_info")
        and isinstance(attr_value, dict)
        and "@type" in attr_value.keys()
        and attr_value["@type"] == "commandResult"
        and "@value" in attr_value.keys()
    )


def is_command_status(attr_key: str, attr_value: str, attr_type: str):
    """
    The attribute is a command status if it is like "command_status" and
    the value:
    "value": {
    "@type": "commandStatus",
    "@value": SOME_VALUE
    }
    """

    return (
        attr_type == "Property"
        and attr_key.endswith("_status")
        and isinstance(attr_value, dict)
        and "@type" in attr_value.keys()
        and attr_value["@type"] == "commandStatus"
        and "@value" in attr_value.keys()
    )


def get_command_name(attr_key: str):
    """
    Get the command name from the attribute key,
    the attribute must be like "command_status" or "command_info"
    """
    return attr_key.split("_")[0]


def is_observed_attribute(attr_value: Any):
    """
    The attribute is in NGSI-LD normalized format. It is observed
    if it is a dict and has the key "observedAt",
    and the type is Property or Relationship.
    Of course, it must have the key "value" or "object" respectively
    """

    return (
        isinstance(attr_value, dict)
        and "observedAt" in attr_value.keys()
        and attr_value["type"] in ["Property", "Relationship", "GeoProperty"]
    )


def has_value(attr_value: Any, attr_type: str):
    """
    The attribute is in NGSI-LD normalized format.
    Returns True if the attribute has a value
    """

    return (
        isinstance(attr_value, dict) and "value" in attr_value.keys()
        if attr_type in ["Property", "GeoProperty"]
        else "object" in attr_value.keys()
    )


def is_jsonld_null(attr_value: Any):
    """
    The attribute is in NGSI-LD normalized format.
    Returns True if the attribute is a null value in jsonld format
    """
    return (
        isinstance(attr_value, dict)
        and "@value" in attr_value.keys()
        and attr_value["@value"] is None
    )


def get_attr_value_and_type(attr_value: Dict, attr_type: str):
    """
    Get the attribute value and type from the attribute value,
    the returned type is transformed to be processed in the platform
    (Property or Relationship, not GeoProperty for the moment)
    """

    attr_transformed_type = None

    match attr_type:
        case "Relationship":
            measure_value = attr_value.get("object", None)
            attr_transformed_type = EntityAttrType.RELATIONSHIP

        case "Property":
            measure_value = attr_value.get("value", None)
            attr_transformed_type = EntityAttrType.PROPERTY

        case "GeoProperty":
            measure_value = attr_value.get("value", None)
            attr_transformed_type = EntityAttrType.PROPERTY

        case _:
            measure_value = attr_value.get("value", None)
            attr_transformed_type = EntityAttrType.PROPERTY
            logging.warning(
                f"Unknown attribute type: {attr_type}, setting it to Property."
            )

    # check if it is a null value in jsonld format
    if is_jsonld_null(measure_value):
        measure_value = None

    return measure_value, attr_transformed_type


def is_valid_ngsi_ld_urn(urn: str) -> bool:
    """
    Validate that a URN follows the NGSI-LD format: urn:ngsi-ld:<type>:<id>
    """
    parts = urn.split(":")
    return len(parts) >= 4 and parts[0] == "urn" and parts[1] == "ngsi-ld"


def get_entity_type_from_urn(urn: str) -> str:
    """
    Urns are like urn:ngsi-ld:<type>:<id>
    This function returns the <type> part
    """

    return urn.split(":")[2]
