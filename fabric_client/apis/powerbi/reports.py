"""Power BI report API operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from fabric_client.core.endpoint import Endpoint

if TYPE_CHECKING:
    from fabric_client.client import FabricClient


class ReportsAPI:
    """API client for Power BI report operations."""

    def __init__(self, client: FabricClient) -> None:
        """Initialize the Reports API client."""
        self._client = client
        self._logger = client._logger_factory.get_logger(__name__)

    async def list(
        self,
        group_id: str | None = None,
        **params: Any,  # noqa: ANN401
    ) -> list[dict[str, object]]:
        """List reports in a workspace (group)."""
        if group_id:
            endpoint = Endpoint("GET", "/groups/{groupId}/reports")
            url = endpoint.build_url(self._client.powerbi_base_url, groupId=group_id)
        else:
            url = f"{self._client.powerbi_base_url}/reports"
        response = await self._client._request("GET", url, params=params)
        return cast("list[dict[str, object]]", response.get("value", []))

    async def get(
        self, report_id: str, group_id: str | None = None
    ) -> dict[str, object]:
        """Get a report by ID."""
        if group_id:
            endpoint = Endpoint("GET", "/groups/{groupId}/reports/{reportId}")
            url = endpoint.build_url(
                self._client.powerbi_base_url,
                groupId=group_id,
                reportId=report_id,
            )
        else:
            url = f"{self._client.powerbi_base_url}/reports/{report_id}"
        return cast("dict[str, object]", await self._client._request("GET", url))

    async def export(
        self,
        report_id: str,
        group_id: str | None = None,
        file_format: str = "PDF",
    ) -> bytes:
        """Export a report to the specified format."""
        if group_id:
            endpoint = Endpoint("POST", "/groups/{groupId}/reports/{reportId}/ExportTo")
            url = endpoint.build_url(
                self._client.powerbi_base_url,
                groupId=group_id,
                reportId=report_id,
            )
        else:
            url = f"{self._client.powerbi_base_url}/reports/{report_id}/ExportTo"
        return cast(
            bytes,
            await self._client._request("POST", url, json={"format": file_format}),
        )
