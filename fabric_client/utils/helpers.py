"""String conversion and dict utilities."""

from __future__ import annotations

import re
from typing import Any


def to_snake_case(name: str) -> str:
    """Convert a CamelCase or PascalCase string to snake_case.

    >>> to_snake_case("displayName")
    'display_name'
    >>> to_snake_case("DatasetId")
    'dataset_id'
    """
    result = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    result = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", result)
    return result.lower()


def to_camel_case(name: str) -> str:
    """Convert a snake_case string to camelCase.

    >>> to_camel_case("display_name")
    'displayName'
    """
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def filter_none(data: dict[str, Any]) -> dict[str, Any]:
    """Remove keys with None values from a dictionary."""
    return {k: v for k, v in data.items() if v is not None}


def extract_id(urn_or_id: str) -> str:
    """Extract a resource ID from a full URN or return the ID as-is."""
    if "/" in urn_or_id:
        return urn_or_id.rsplit("/", 1)[-1]
    return urn_or_id
