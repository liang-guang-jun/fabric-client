"""Fabric generic items API operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from fabric_client.core.endpoint import Endpoint

if TYPE_CHECKING:
    from fabric_client.client import FabricClient


class ItemsAPI:
    """API client for generic Fabric item operations (CRUD across all item types)."""

    def __init__(self, client: FabricClient) -> None:
        """Initialize the Items API client."""
        self._client = client
        self._logger = client._logger_factory.get_logger(__name__)

    async def list(
        self,
        workspace_id: str,
        item_type: str | None = None,
        **params: Any,  # noqa: ANN401
    ) -> list[dict[str, object]]:
        """List items in a workspace, optionally filtered by type."""
        self._logger.debug(
            "Listing items in workspace=%s type=%s",
            workspace_id,
            item_type,
        )
        endpoint = Endpoint("GET", "/workspaces/{workspaceId}/items")
        url = endpoint.build_url(self._client.base_url, workspaceId=workspace_id)
        if item_type:
            params["type"] = item_type
        response = await self._client._request("GET", url, params=params)
        return cast("list[dict[str, object]]", response.get("value", []))

    async def get(self, workspace_id: str, item_id: str) -> dict[str, object]:
        """Get a specific item by ID."""
        endpoint = Endpoint("GET", "/workspaces/{workspaceId}/items/{itemId}")
        url = endpoint.build_url(
            self._client.base_url, workspaceId=workspace_id, itemId=item_id
        )
        return cast("dict[str, object]", await self._client._request("GET", url))

    async def create(
        self,
        workspace_id: str,
        display_name: str,
        item_type: str,
        definition: dict[str, Any] | None = None,
    ) -> dict[str, object]:
        """Create a new item in a workspace."""
        endpoint = Endpoint("POST", "/workspaces/{workspaceId}/items")
        url = endpoint.build_url(self._client.base_url, workspaceId=workspace_id)
        body: dict[str, Any] = {
            "displayName": display_name,
            "type": item_type,
        }
        if definition:
            body["definition"] = definition
        return cast(
            "dict[str, object]",
            await self._client._request("POST", url, json=body),
        )

    async def update(
        self,
        workspace_id: str,
        item_id: str,
        **updates: Any,  # noqa: ANN401
    ) -> dict[str, object]:
        """Update an existing item."""
        endpoint = Endpoint("PATCH", "/workspaces/{workspaceId}/items/{itemId}")
        url = endpoint.build_url(
            self._client.base_url, workspaceId=workspace_id, itemId=item_id
        )
        return cast(
            "dict[str, object]",
            await self._client._request("PATCH", url, json=updates),
        )

    async def delete(self, workspace_id: str, item_id: str) -> None:
        """Delete an item from a workspace."""
        endpoint = Endpoint("DELETE", "/workspaces/{workspaceId}/items/{itemId}")
        url = endpoint.build_url(
            self._client.base_url, workspaceId=workspace_id, itemId=item_id
        )
        await self._client._request("DELETE", url)

    async def get_definition(
        self, workspace_id: str, item_id: str
    ) -> dict[str, object]:
        """Get the definition (parts) of a Fabric item (Gen2 dataflow, etc.)."""
        endpoint = Endpoint(
            "POST",
            "/workspaces/{workspaceId}/items/{itemId}/getDefinition",
        )
        url = endpoint.build_url(
            self._client.base_url, workspaceId=workspace_id, itemId=item_id
        )
        return cast(
            "dict[str, object]",
            await self._client._request("POST", url),
        )
