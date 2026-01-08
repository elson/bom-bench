"""Utility functions for bom-bench."""

from __future__ import annotations

from typing import Any

from expandvars import expandvars


def expandvars_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively expand all string values in a dictionary using expandvars."""

    def expand_item(item: Any) -> Any:
        if isinstance(item, str):
            return expandvars(item)
        if isinstance(item, dict):
            return expandvars_dict(item)
        if isinstance(item, list):
            return [expand_item(i) for i in item]
        return item

    return {key: expand_item(value) for key, value in data.items()}
