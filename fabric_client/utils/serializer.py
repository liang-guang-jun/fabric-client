"""JSON serialization helpers."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any


class Serializer:
    """Handles serialization/deserialization of Fabric API objects."""

    @staticmethod
    def to_json(data: dict[str, Any], indent: int | None = None) -> str:
        """Serialize a dictionary to a JSON string."""
        return json.dumps(
            data, default=Serializer._default_serializer, indent=indent
        )

    @staticmethod
    def from_json(json_str: str | bytes) -> Any:  # noqa: ANN401
        """Deserialize a JSON string to a dictionary."""
        return json.loads(json_str)

    @staticmethod
    def _default_serializer(obj: Any) -> Any:  # noqa: ANN401
        """Handle non-JSON-serializable types."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        raise TypeError(
            f"Object of type {type(obj).__name__} is not JSON serializable"
        )

    @staticmethod
    def serialize_model(obj: Any) -> Any:  # noqa: ANN401
        """Serialize a model instance to a dictionary suitable for API requests."""
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        if isinstance(obj, dict):
            return {k: Serializer.serialize_model(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [Serializer.serialize_model(item) for item in obj]
        return obj
