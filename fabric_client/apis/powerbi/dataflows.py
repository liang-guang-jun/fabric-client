"""Power BI dataflow API operations."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, cast

from fabric_client.core.endpoint import Endpoint
from fabric_client.models.dataflow import DataflowTransaction

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
            url = endpoint.build_url(self._client.powerbi_base_url, groupId=group_id)
        else:
            url = f"{self._client.powerbi_base_url}/dataflows"
        response = await self._client._request("GET", url, params=params)
        return cast("list[dict[str, object]]", response.get("value", []))

    async def get(
        self, dataflow_id: str, group_id: str | None = None
    ) -> dict[str, object]:
        """Get a dataflow by ID."""
        if group_id:
            endpoint = Endpoint("GET", "/groups/{groupId}/dataflows/{dataflowId}")
            url = endpoint.build_url(
                self._client.powerbi_base_url,
                groupId=group_id,
                dataflowId=dataflow_id,
            )
        else:
            url = f"{self._client.powerbi_base_url}/dataflows/{dataflow_id}"
        return cast("dict[str, object]", await self._client._request("GET", url))

    async def refresh(
        self,
        dataflow_id: str,
        group_id: str | None = None,
        *,
        process_type: str | None = None,
        notify_option: str = "NoNotification",
        force: bool = False,
        wait: bool = False,
        timeout: int = 7200,
    ) -> list[DataflowTransaction] | None:
        """Trigger a dataflow refresh, optionally waiting for completion.

        Args:
            dataflow_id: The dataflow to refresh.
            group_id: Workspace (group) identifier.
            process_type: Optional process type parameter.
            notify_option: ``MailOnFailure`` or ``NoNotification``.
            force: Cancel any active transaction before starting.
            wait: Poll until refresh completes.
            timeout: Maximum seconds to wait (default 7200).
        """
        if group_id is None:
            group_id = ""
        if force:
            latest = await self._latest_transaction(
                group_id=group_id, dataflow_id=dataflow_id
            )
            if latest and self._is_active_transaction(latest):
                await self.cancel_transaction(
                    group_id=group_id, transaction_id=latest.id
                )
                await asyncio.sleep(2)

        baseline = (
            await self._latest_transaction(group_id=group_id, dataflow_id=dataflow_id)
            if wait
            else None
        )

        params: dict[str, str] | None = None
        if process_type is not None:
            params = {"processType": process_type}
        payload: dict[str, object] = {"notifyOption": notify_option}

        endpoint = Endpoint(
            "POST",
            "/groups/{groupId}/dataflows/{dataflowId}/refreshes",
        )
        url = endpoint.build_url(
            self._client.powerbi_base_url,
            groupId=group_id,
            dataflowId=dataflow_id,
        )
        if params:
            url_params = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{url}?{url_params}"
        await self._client._request("POST", url, json=payload)

        if not wait:
            return None
        return await self._wait_for_refresh(
            group_id=group_id,
            dataflow_id=dataflow_id,
            baseline_id=(None if baseline is None else baseline.id),
            timeout=timeout,
        )

    async def list_transactions(
        self, group_id: str, dataflow_id: str
    ) -> list[DataflowTransaction]:
        """List refresh transactions for a dataflow."""
        endpoint = Endpoint(
            "GET", "/groups/{groupId}/dataflows/{dataflowId}/transactions"
        )
        url = endpoint.build_url(
            self._client.powerbi_base_url, groupId=group_id, dataflowId=dataflow_id
        )
        response = await self._client._request("GET", url)
        raw = cast("list[dict[str, object]]", response.get("value", []))
        result = [DataflowTransaction.model_validate(r) for r in raw]
        for tx in result:
            tx.workspace_id = group_id
            tx.dataflow_id = dataflow_id
        return result

    async def cancel_transaction(self, group_id: str, transaction_id: str) -> None:
        """Cancel an active dataflow transaction."""
        endpoint = Endpoint(
            "POST",
            "/groups/{groupId}/dataflows/transactions/{transactionId}/cancel",
        )
        url = endpoint.build_url(
            self._client.powerbi_base_url,
            groupId=group_id,
            transactionId=transaction_id,
        )
        await self._client._request("POST", url)

    # -- transaction helpers --------------------------------------------------

    async def _latest_transaction(
        self, group_id: str, dataflow_id: str
    ) -> DataflowTransaction | None:
        txs: list[DataflowTransaction] = await self.list_transactions(
            group_id=group_id, dataflow_id=dataflow_id
        )
        if not txs:
            return None
        return txs[0]

    @staticmethod
    def _is_active_transaction(tx: DataflowTransaction) -> bool:
        return tx.status in ("InProgress", "PendingExecution", "Scheduled")

    @staticmethod
    def _is_success_transaction(tx: DataflowTransaction) -> bool:
        return tx.status == "Success"

    @staticmethod
    def _is_failure_transaction(tx: DataflowTransaction) -> bool:
        return tx.status == "Failed"

    async def _wait_for_refresh(
        self,
        group_id: str,
        dataflow_id: str,
        baseline_id: str | None,
        timeout: int,
    ) -> list[DataflowTransaction]:
        """Poll transactions every 10s until completion or timeout."""
        elapsed = 0

        while elapsed <= timeout:
            latest = await self._latest_transaction(
                group_id=group_id, dataflow_id=dataflow_id
            )
            if latest and latest.id != baseline_id:
                if self._is_success_transaction(latest):
                    return [latest]
                if self._is_failure_transaction(latest):
                    raise RuntimeError(f"Dataflow refresh failed: {latest.status}")
            sleep = min(10, timeout - elapsed) if timeout > elapsed else 0
            if sleep <= 0:
                break
            await asyncio.sleep(sleep)
            elapsed += sleep

        raise RuntimeError(f"Dataflow refresh did not finish within {timeout}s")

    async def export_definition(self, dataflow_id: str) -> dict[str, object]:
        """Export the full definition of a Gen1 dataflow via the admin API.

        Returns the complete JSON response.
        """
        url = f"{self._client.powerbi_base_url}/admin/dataflows/{dataflow_id}/export"
        response = await self._client._request("GET", url)
        return cast("dict[str, object]", response)
