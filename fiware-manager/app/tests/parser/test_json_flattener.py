from app.core.parser.json_flattener import JsonFlattener


class TestJsonFlattenerDefault:
    def test_one_level_dissolved_by_default(self):
        out = JsonFlattener().flatten({"a": 1, "section": {"b": 2, "c": 3}})
        assert out == {"a": 1, "b": 2, "c": 3}

    def test_non_dict_values_passed_through(self):
        out = JsonFlattener().flatten({"a": 1, "list": [1, 2, 3], "string": "x"})
        assert out == {"a": 1, "list": [1, 2, 3], "string": "x"}

    def test_location_skipped(self):
        out = JsonFlattener().flatten(
            {"location": {"type": "Point", "coordinates": [2.2, 41.4]}}
        )
        assert out == {"location": {"type": "Point", "coordinates": [2.2, 41.4]}}

    def test_custom_skipped_section(self):
        flattener = JsonFlattener(sections_to_skip=["raw"])
        out = flattener.flatten({"raw": {"a": 1}, "section": {"b": 2}})
        assert out == {"raw": {"a": 1}, "b": 2}


class TestMaxDepth:
    def test_max_depth_zero_returns_copy(self):
        data = {"a": {"b": {"c": 1}}}
        out = JsonFlattener(max_depth=0).flatten(data)
        assert out == {"a": {"b": {"c": 1}}}

    def test_max_depth_two_dissolves_two_levels(self):
        data = {"a": {"b": {"c": 1}}}
        out = JsonFlattener(max_depth=2).flatten(data)
        assert out == {"c": 1}

    def test_max_depth_overridable_per_call(self):
        flattener = JsonFlattener(max_depth=1)
        deep = {"a": {"b": {"c": 1}}}
        assert flattener.flatten(deep) == {"b": {"c": 1}}
        assert flattener.flatten(deep, max_depth=2) == {"c": 1}

    def test_unlimited_depth(self):
        data = {"a": {"b": {"c": {"d": {"e": 1}}}}}
        out = JsonFlattener(max_depth=-1).flatten(data)
        assert out == {"e": 1}

    def test_max_depth_does_not_dive_into_skipped(self):
        flattener = JsonFlattener(max_depth=-1)
        out = flattener.flatten(
            {"location": {"type": "Point", "coordinates": [1, 2]}}
        )
        assert out == {"location": {"type": "Point", "coordinates": [1, 2]}}
