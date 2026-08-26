"""Generic JSON flattener with configurable depth."""

from typing import Any

DEFAULT_SECTIONS_TO_SKIP = ["location"]


class JsonFlattener:
    """Dissolves nested dicts up to `max_depth` levels (`-1` = unlimited)."""

    def __init__(self,sections_to_skip: list[str] | None = None,max_depth: int = 1):
        skip = list(DEFAULT_SECTIONS_TO_SKIP)
        if sections_to_skip:
            skip.extend(sections_to_skip)
        self.sections_to_skip = set(skip)
        self.max_depth = max_depth

    def flatten(self, data: dict, max_depth: int | None = None) -> dict:
        """Flatten `data`. Pass `max_depth` to override the instance default."""
        depth = self.max_depth if max_depth is None else max_depth
        return self._dissolve(data, depth)

    def _dissolve(self, data: dict, depth: int) -> dict:
        if depth == 0:
            return dict(data)
        result: dict[str, Any] = {}
        for key, value in data.items():
            if key in self.sections_to_skip or not isinstance(value, dict):
                result[key] = value
                continue
            next_depth = depth - 1 if depth > 0 else depth
            for sub_key, sub_value in self._dissolve(value, next_depth).items():
                result[sub_key] = sub_value
        return result
