"""API endpoint descriptor (method + path template)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Endpoint:
    """Describes an API endpoint with its HTTP method, path, and parameter schema."""

    method: str  # GET, POST, PUT, PATCH, DELETE
    path: str  # e.g. "/workspaces/{workspaceId}/items"
    description: str = ""

    # Default query parameters applied to every request
    default_params: dict[str, Any] = field(default_factory=dict)

    # Expected path parameter names parsed from the path template
    path_params: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Auto-extract path parameters from the template."""
        if not self.path_params:
            # Auto-extract path parameters from the template
            self.path_params = tuple(
                part.strip("{}")
                for part in self.path.split("/")
                if part.startswith("{")
            )

    def build_url(self, base_url: str, **path_values: str) -> str:
        """Build the full URL by substituting path parameters."""
        url = f"{base_url.rstrip('/')}{self.path}"
        return url.format(**path_values)
