from typing import Dict


def build_headers(tenant: str, scope: str) -> Dict[str, str]:
    """
    Build the general headers for any request to the Context Broker
    """
    return {
        "fiware-service": tenant,
        "fiware-servicepath": scope,
    }


def schema_to_json(s) -> dict:
    """
    Transform a pydantic schema to a json, removing None values
    """
    return remove_none_values_recursive(s.dict())


def remove_none_values_recursive(d: dict) -> dict:
    """
    Remove None values from a dictionary recursively
    """
    if not isinstance(d, dict):
        return d
    new_d = {}
    for k, v in d.items():
        if v is None:
            continue
        if isinstance(v, dict):
            v = remove_none_values_recursive(v)
        if isinstance(v, list):
            v = [remove_none_values_recursive(vi) for vi in v]
        new_d[k] = v

    return new_d
