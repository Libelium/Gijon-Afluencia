from typing import Dict


def build_headers(tenant: str, scope: str, context_url: str) -> Dict[str, str]:
    """
    Build the general headers for any request to the Context Broker
    """
    return {
        "Link": build_context_link_header(context_url),
        "NGSILD-Tenant": tenant,
        "Accept": "application/ld+json",
    }


def build_context_link_header(context_url: str) -> str:
    """
    Build context link header value
    """
    return f'<{context_url}>; rel="http://www.w3.org/ns/json-ld#context"; type="application/ld+json"'


def to_ngsi_null_if_none(value):
    """
    Transform a value to ngsi null if it is None
    """
    return value if value is not None else {"@type": "@json", "@value": None}


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
