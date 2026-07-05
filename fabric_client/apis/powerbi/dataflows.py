"""Power BI dataflow API operations."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

from fabric_client.core.endpoint import Endpoint

if TYPE_CHECKING:
    from fabric_client.client import FabricClient

logger = logging.getLogger(__name__)


class DataflowsAPI:
    """API client for Power BI dataflow operations."""

    def __init__(self, client: FabricClient) -> None:
        """Initialize the Dataflows API client."""
        self._client = client

    async def list(
        self,
        group_id: str | None = None,
        **params: Any,  # noqa: ANN401
    ) -> list[dict[str, object]]:
        """List dataflows in a workspace (group)."""
        if group_id:
            endpoint = Endpoint("GET", "/groups/{groupId}/dataflows")
            url = endpoint.build_url(
                self._client.powerbi_base_url, groupId=group_id
            )
        else:
            url = f"{self._client.powerbi_base_url}/dataflows"
        response = await self._client._request("GET", url, params=params)
        return cast("list[dict[str, object]]", response.get("value", []))

    async def get(
        self, dataflow_id: str, group_id: str | None = None
    ) -> dict[str, object]:
        """Get a dataflow by ID."""
        if group_id:
            endpoint = Endpoint(
                "GET", "/groups/{groupId}/dataflows/{dataflowId}"
            )
            url = endpoint.build_url(
                self._client.powerbi_base_url,
                groupId=group_id,
                dataflowId=dataflow_id,
            )
        else:
            url = f"{self._client.powerbi_base_url}/dataflows/{dataflow_id}"
        return cast(
            "dict[str, object]", await self._client._request("GET", url)
        )

    async def refresh(
        self, dataflow_id: str, group_id: str | None = None
    ) -> None:
        """Trigger a refresh of a dataflow."""
        if group_id:
            endpoint = Endpoint(
                "POST",
                "/groups/{groupId}/dataflows/{dataflowId}/refreshes",
            )
            url = endpoint.build_url(
                self._client.powerbi_base_url,
                groupId=group_id,
                dataflowId=dataflow_id,
            )
        else:
            url = f"{self._client.powerbi_base_url}/dataflows/{dataflow_id}/refreshes"
        await self._client._request("POST", url)
