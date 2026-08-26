from typing import Any, Callable, Dict, List
from aether_pylib.iota.iota_provision_payload import (
    DeviceProvisionPayload,
    DeviceDef,
)


def bulk_ld_2_v2(provision_payload: DeviceProvisionPayload) -> DeviceProvisionPayload:
    """
    Same as ld_2_v2 but for a list of devices.
    """

    return DeviceProvisionPayload(
        devices=[ld_2_v2(device_def) for device_def in provision_payload.devices]
    )


def ld_2_v2_attributes(attributes: List[Dict]) -> List[Dict]:
    """
    Translate a list of attributes from NGSI-LD to NGSI-v2.
    Attributes are type "Property" in LD, but in v2 they can be
    Null, Number, String, Object, Array or Boolean
    Because we do not know the type of the attribute, we just translate it to Object.
    """

    for attribute in attributes:
        attribute["type"] = "Object"

    return attributes


def ld_2_v2_commands(commands: List[Dict]) -> List[Dict]:
    """
    Translate a list of commands from NGSI-LD to NGSI-v2.
    Commands are type "Property" in LD, but "command" in v2.
    """

    for command in commands:
        command["type"] = "command"

    return commands


def ld_2_v2_static_attributes(static_attributes: List[Dict]) -> List[Dict]:
    """
    Translate a list of static attributes from NGSI-LD to NGSI-v2.
    Same problem than with attributes, but in this case we can check
    the value of the attribute to determine its type.
    """

    for static_attribute in static_attributes:
        value = static_attribute.get("value", None)
        if value is None:
            static_attribute["type"] = "Object"
        elif isinstance(value, bool):
            static_attribute["type"] = "Boolean"
        elif isinstance(value, int) or isinstance(value, float):
            static_attribute["type"] = "Number"
        elif isinstance(value, list):
            static_attribute["type"] = "Array"
        elif isinstance(value, str):
            static_attribute["type"] = "String"
        else:
            static_attribute["type"] = "Object"

    return static_attributes


TRANSLATION_MAP: Dict[str, Callable[[Any], Any]] = {
    "attributes": ld_2_v2_attributes,
    "commands": ld_2_v2_commands,
    "static_attributes": ld_2_v2_static_attributes,
}


def ld_2_v2(device_def: DeviceDef) -> DeviceDef:
    """
    Translate a device definition from NGSI-LD to NGSI-v2.
    It turns out that DeviceDef is compatible with the NGSI-v2 format,
    so we return the same type with some little modifications.
    """

    dict_device_def = device_def.model_dump()

    for key, value in dict_device_def.items():
        translation_func = TRANSLATION_MAP.get(key, None)
        if translation_func:
            dict_device_def[key] = translation_func(value)

    return DeviceDef(**dict_device_def)
