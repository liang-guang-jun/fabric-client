"""Power BI dataset API operations."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

from fabric_client.core.endpoint import Endpoint

if TYPE_CHECKING:
    from fabric_client.client import FabricClient

logger = logging.getLogger(__name__)


class DatasetsAPI:
    """API client for Power BI dataset operations."""

    def __init__(self, client: FabricClient) -> None:
        """Initialize the Datasets API client."""
        self._client = client

    async def list(
        self,
        group_id: str | None = None,
        **params: Any,  # noqa: ANN401
    ) -> list[dict[str, object]]:
        """List datasets in a workspace (group)."""
        if group_id:
            endpoint = Endpoint("GET", "/groups/{groupId}/datasets")
            url = endpoint.build_url(
                self._client.powerbi_base_url, groupId=group_id
            )
        else:
            url = f"{self._client.powerbi_base_url}/datasets"
        response = await self._client._request("GET", url, params=params)
        return cast("list[dict[str, object]]", response.get("value", []))

    async def get(
        self, dataset_id: str, group_id: str | None = None
    ) -> dict[str, object]:
        """Get a dataset by ID."""
        if group_id:
            endpoint = Endpoint(
                "GET", "/groups/{groupId}/datasets/{datasetId}"
            )
            url = endpoint.build_url(
                self._client.powerbi_base_url,
                groupId=group_id,
                datasetId=dataset_id,
            )
        else:
            url = f"{self._client.powerbi_base_url}/datasets/{dataset_id}"
        return cast(
            "dict[str, object]", await self._client._request("GET", url)
        )

    async def refresh(
        self, dataset_id: str, group_id: str | None = None
    ) -> None:
        """Trigger a refresh of a dataset."""
        if group_id:
            endpoint = Endpoint(
                "POST",
                "/groups/{groupId}/datasets/{datasetId}/refreshes",
            )
            url = endpoint.build_url(
                self._client.powerbi_base_url,
                groupId=group_id,
                datasetId=dataset_id,
            )
        else:
            url = f"{self._client.powerbi_base_url}/datasets/{dataset_id}/refreshes"
        await self._client._request("POST", url)

    async def delete(
        self, dataset_id: str, group_id: str | None = None
    ) -> None:
        """Delete a dataset."""
        if group_id:
            endpoint = Endpoint(
                "DELETE", "/groups/{groupId}/datasets/{datasetId}"
            )
            url = endpoint.build_url(
                self._client.powerbi_base_url,
                groupId=group_id,
                datasetId=dataset_id,
            )
        else:
            url = f"{self._client.powerbi_base_url}/datasets/{dataset_id}"
        await self._client._request("DELETE", url)
