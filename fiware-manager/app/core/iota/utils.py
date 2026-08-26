from typing import Dict


def attr_translation(
    payload: dict, translation_map: Dict[str, str], append_mode: bool = False
) -> dict:
    """
    Translates attributes from a dictionary using a translation map
    Translation map is a dictionary where the key is the original attribute name
    and the value is the new attribute name
    ej:
    translation_map = {'old_name': 'new_name'}

    if append_mode is True, the new attributes will be appended to the payload
    """

    if append_mode:
        return {
            **payload,
            **{translation_map.get(key, key): value for key, value in payload.items()},
        }

    return {translation_map.get(key, key): value for key, value in payload.items()}
