from datetime import datetime

"""
This module contains functions to process NGSI-LD entities, 
and extract some useful information from them (temporal attributes, values, etc).
"""

# normalized value for an attribute
normalized_value_key = "value"  

# value for an attribute in the schema (not normalized)
schema_value_key = "@value"  

# possible keys for the value of an attribute
possible_value_keys = [
    normalized_value_key,
    schema_value_key,
]  

# possible keys for the temporal value of an attribute
possible_temporal_keys = [
    "timestamp",
    "observedAt",
    "modifiedAt",
    "createdAt",
]  


def get_first_key_in_list_from_dict(dict: dict, keys: list):
    """
    Get the first key in the list that is present in the dict
    """
    for key in keys:
        key_value = dict.get(key, None)
        if key_value is not None:
            break
    return key_value


def has_value(dict: dict):
    """
    Check if the dict has a value property
    """
    return any(key in dict for key in possible_value_keys)


def has_temporal(dict: dict):
    """
    Check if the dict has a temporal property
    """
    return any(key in dict for key in possible_temporal_keys)


def get_value_property_from_normalized_attribute(attribute: dict):
    """
    get the value property from a normalized ngsi-ld attribute
    """
    return get_first_key_in_list_from_dict(attribute, possible_value_keys)


def get_temporal_property_from_normalized_attribute(attribute: dict) -> datetime:
    """
    get the temporal property from a normalized ngsi-ld attribute
    """
    str_datetime = get_first_key_in_list_from_dict(attribute, possible_temporal_keys)
    if str_datetime is None:
        return None
    return datetime.fromisoformat(str_datetime)
