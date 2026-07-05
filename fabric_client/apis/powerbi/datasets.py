"""Power BI dataset API operations."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, cast

from fabric_client.core.endpoint import Endpoint
from fabric_client.models.dataset import DatasetRefresh

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
            url = endpoint.build_url(self._client.powerbi_base_url, groupId=group_id)
        else:
            url = f"{self._client.powerbi_base_url}/datasets"
        response = await self._client._request("GET", url, params=params)
        return cast("list[dict[str, object]]", response.get("value", []))

    async def get(
        self, dataset_id: str, group_id: str | None = None
    ) -> dict[str, object]:
        """Get a dataset by ID."""
        if group_id:
            endpoint = Endpoint("GET", "/groups/{groupId}/datasets/{datasetId}")
            url = endpoint.build_url(
                self._client.powerbi_base_url,
                groupId=group_id,
                datasetId=dataset_id,
            )
        else:
            url = f"{self._client.powerbi_base_url}/datasets/{dataset_id}"
        return cast("dict[str, object]", await self._client._request("GET", url))

    async def refresh(
        self,
        dataset_id: str,
        group_id: str | None = None,
        *,
        notify_option: str = "NoNotification",
        force: bool = False,
        wait: bool = False,
        timeout: int = 7200,
    ) -> list[DatasetRefresh] | None:
        """Trigger a dataset refresh, optionally waiting for completion.

        Args:
            dataset_id: The dataset to refresh.
            group_id: Workspace (group) identifier.
            notify_option: ``MailOnFailure`` or ``NoNotification``.
            force: Cancel any active refresh before starting.
            wait: Poll until refresh completes.
            timeout: Maximum seconds to wait (default 7200).
        """
        if group_id is None:
            group_id = ""

        if force:
            latest = await self._latest_refresh(
                group_id=group_id, dataset_id=dataset_id
            )
            if latest and self._is_active_refresh(latest):
                await self.cancel_refresh(
                    group_id=group_id,
                    dataset_id=dataset_id,
                    refresh_id=latest.request_id,
                )
                # Give the cancellation a moment to propagate
                await asyncio.sleep(2)

        baseline = (
            await self._latest_refresh(group_id=group_id, dataset_id=dataset_id)
            if wait
            else None
        )

        payload: dict[str, object] = {"notifyOption": notify_option}
        endpoint = Endpoint("POST", "/groups/{groupId}/datasets/{datasetId}/refreshes")
        url = endpoint.build_url(
            self._client.powerbi_base_url,
            groupId=group_id,
            datasetId=dataset_id,
        )
        await self._client._request("POST", url, json=payload)

        if not wait:
            return None
        return await self._wait_for_refresh(
            group_id=group_id,
            dataset_id=dataset_id,
            baseline_request_id=(None if baseline is None else baseline.request_id),
            timeout=timeout,
        )

    async def list_refreshes(
        self, group_id: str, dataset_id: str, top: int | None = None
    ) -> list[DatasetRefresh]:
        """List refresh history for a dataset."""
        params: dict[str, str] | None = {"$top": str(top)} if top else None
        endpoint = Endpoint("GET", "/groups/{groupId}/datasets/{datasetId}/refreshes")
        url = endpoint.build_url(
            self._client.powerbi_base_url,
            groupId=group_id,
            datasetId=dataset_id,
        )
        response = await self._client._request("GET", url, params=params)
        raw = cast("list[dict[str, object]]", response.get("value", []))
        result = [DatasetRefresh.model_validate(r) for r in raw]
        for r in result:
            r.workspace_id = group_id
            r.dataset_id = dataset_id
        return result

    async def get_refresh_details(
        self, group_id: str, dataset_id: str, refresh_id: str
    ) -> dict[str, object]:
        """Get detailed execution info for a dataset refresh."""
        endpoint = Endpoint(
            "GET",
            "/groups/{groupId}/datasets/{datasetId}/refreshes/{refreshId}",
        )
        url = endpoint.build_url(
            self._client.powerbi_base_url,
            groupId=group_id,
            datasetId=dataset_id,
            refreshId=refresh_id,
        )
        return cast("dict[str, object]", await self._client._request("GET", url))

    async def cancel_refresh(
        self, group_id: str, dataset_id: str, refresh_id: str
    ) -> None:
        """Cancel an in-progress dataset refresh."""
        endpoint = Endpoint(
            "DELETE",
            "/groups/{groupId}/datasets/{datasetId}/refreshes/{refreshId}",
        )
        url = endpoint.build_url(
            self._client.powerbi_base_url,
            groupId=group_id,
            datasetId=dataset_id,
            refreshId=refresh_id,
        )
        await self._client._request("DELETE", url)

    # -- refresh helpers ------------------------------------------------------

    async def _latest_refresh(
        self, group_id: str, dataset_id: str
    ) -> DatasetRefresh | None:
        refs: list[DatasetRefresh] = await self.list_refreshes(
            group_id=group_id, dataset_id=dataset_id, top=1
        )
        if not refs:
            return None
        return refs[0]

    @staticmethod
    def _is_active_refresh(refresh: DatasetRefresh) -> bool:
        return refresh.status in ("Unknown", "InProgress", "NotStarted")

    @staticmethod
    def _is_success_refresh(refresh: DatasetRefresh) -> bool:
        return refresh.status == "Completed"

    @staticmethod
    def _is_failure_refresh(refresh: DatasetRefresh) -> bool:
        return refresh.status == "Failed"

    async def _wait_for_refresh(
        self,
        group_id: str,
        dataset_id: str,
        baseline_request_id: str | None,
        timeout: int,
    ) -> list[DatasetRefresh]:
        """Poll refreshes every 10s until completion or timeout."""
        elapsed = 0

        while elapsed <= timeout:
            latest = await self._latest_refresh(
                group_id=group_id, dataset_id=dataset_id
            )
            if latest and latest.request_id != baseline_request_id:
                if self._is_success_refresh(latest):
                    return [latest]
                if self._is_failure_refresh(latest):
                    raise RuntimeError(f"Dataset refresh failed: {latest.status}")
            sleep = min(10, timeout - elapsed) if timeout > elapsed else 0
            if sleep <= 0:
                break
            await asyncio.sleep(sleep)
            elapsed += sleep

        raise RuntimeError(f"Dataset refresh did not finish within {timeout}s")

    async def delete(self, dataset_id: str, group_id: str | None = None) -> None:
        """Delete a dataset."""
        if group_id:
            endpoint = Endpoint("DELETE", "/groups/{groupId}/datasets/{datasetId}")
            url = endpoint.build_url(
                self._client.powerbi_base_url,
                groupId=group_id,
                datasetId=dataset_id,
            )
        else:
            url = f"{self._client.powerbi_base_url}/datasets/{dataset_id}"
        await self._client._request("DELETE", url)
