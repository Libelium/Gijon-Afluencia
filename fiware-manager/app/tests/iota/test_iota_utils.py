import pytest
from app.core.iota.utils import attr_translation


class TestIotaUtils:

    @pytest.mark.parametrize(
        "payload, translation_map, expected",
        [
            (
                {
                    "m1": 1,
                    "m2": "a",
                    "m3": 3.0,
                    "m4": True,
                    "m5": {
                        "type": "Property",
                        "value": "value",
                    },
                    "m6": 2,
                    "m7": "b",
                    "m8": 4.0,
                    "m9": False,
                    "m10": {
                        "type": "Property2",
                        "value": "value2",
                    },
                },
                {
                    "m1": "new_m1",
                    "m2": "new_m2",
                    "m3": "new_m3",
                    "m4": "new_m4",
                    "m5": "new_m5",
                },
                {
                    "new_m1": 1,
                    "new_m2": "a",
                    "new_m3": 3.0,
                    "new_m4": True,
                    "new_m5": {
                        "type": "Property",
                        "value": "value",
                    },
                    "m6": 2,
                    "m7": "b",
                    "m8": 4.0,
                    "m9": False,
                    "m10": {
                        "type": "Property2",
                        "value": "value2",
                    },
                },
            ),
        ],
    )
    def test_iota_translation_map(
        self, payload: dict, translation_map: dict, expected: dict
    ):

        result = attr_translation(payload, translation_map)

        assert result == expected

    @pytest.mark.parametrize(
        "payload, translation_map, expected",
        [
            (
                {
                    "m1": 1,
                    "m2": "a",
                    "m3": 3.0,
                    "m4": True,
                    "m5": {
                        "type": "Property",
                        "value": "value",
                    },
                    "m6": 2,
                    "m7": "b",
                    "m8": 4.0,
                    "m9": False,
                    "m10": {
                        "type": "Property2",
                        "value": "value2",
                    },
                },
                {
                    "m1": "new_m1",
                    "m2": "new_m2",
                    "m3": "new_m3",
                    "m4": "new_m4",
                    "m5": "new_m5",
                },
                {
                    "m1": 1,
                    "m2": "a",
                    "m3": 3.0,
                    "m4": True,
                    "m5": {
                        "type": "Property",
                        "value": "value",
                    },
                    "m6": 2,
                    "m7": "b",
                    "m8": 4.0,
                    "m9": False,
                    "m10": {
                        "type": "Property2",
                        "value": "value2",
                    },
                    "new_m1": 1,
                    "new_m2": "a",
                    "new_m3": 3.0,
                    "new_m4": True,
                    "new_m5": {
                        "type": "Property",
                        "value": "value",
                    },
                },
            ),
        ],
    )
    def test_iota_translation_map_append(
        self, payload: dict, translation_map: dict, expected: dict
    ):

        result = attr_translation(payload, translation_map, append_mode=True)

        assert result == expected
