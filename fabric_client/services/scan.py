"""Admin workspace scan service."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from fabric_client.models.scan import WorkspaceScanResult

if TYPE_CHECKING:
    from fabric_client.client import FabricClient

logger = logging.getLogger(__name__)

_SCAN_BATCH_SIZE = 100


class WorkspaceScanService:
    """Orchestrate admin workspace scans.

    Usage::

        scan = WorkspaceScanService(client)
        results = await scan.scan(["ws-id-1", "ws-id-2"])
        for r in results:
            print(r.datasets)
    """

    def __init__(self, client: FabricClient) -> None:
        """Initialize with a client."""
        self._client = client

    async def scan(
        self,
        workspace_ids: list[str],
        *,
        lineage: bool = True,
        datasource_details: bool = True,
        dataset_schema: bool = True,
        dataset_expressions: bool = True,
        get_artifact_users: bool = True,
        timeout: int = 7200,
    ) -> list[WorkspaceScanResult]:
        """Scan one or more workspaces and return merged results."""
        if not workspace_ids:
            raise ValueError("workspace_ids must not be empty")

        # Split into batches of up to 100
        batches = [
            workspace_ids[i : i + _SCAN_BATCH_SIZE]
            for i in range(0, len(workspace_ids), _SCAN_BATCH_SIZE)
        ]

        if len(batches) == 1:
            return await self._scan_batch(
                workspace_ids=batches[0],
                lineage=lineage,
                datasource_details=datasource_details,
                dataset_schema=dataset_schema,
                dataset_expressions=dataset_expressions,
                get_artifact_users=get_artifact_users,
                timeout=timeout,
            )

        # Parallel batches
        tasks = [
            self._scan_batch(
                workspace_ids=b,
                lineage=lineage,
                datasource_details=datasource_details,
                dataset_schema=dataset_schema,
                dataset_expressions=dataset_expressions,
                get_artifact_users=get_artifact_users,
                timeout=timeout,
            )
            for b in batches
        ]
        batch_results = await asyncio.gather(*tasks)
        merged: list[WorkspaceScanResult] = []
        for br in batch_results:
            merged.extend(br)
        return merged

    async def _scan_batch(
        self,
        workspace_ids: list[str],
        *,
        lineage: bool,
        datasource_details: bool,
        dataset_schema: bool,
        dataset_expressions: bool,
        get_artifact_users: bool,
        timeout: int,
    ) -> list[WorkspaceScanResult]:
        """Run one admin scan batch and poll until complete."""
        scan_id = await self._post_scan(
            workspace_ids,
            lineage=lineage,
            datasource_details=datasource_details,
            dataset_schema=dataset_schema,
            dataset_expressions=dataset_expressions,
            get_artifact_users=get_artifact_users,
        )
        await self._poll_scan(scan_id, timeout=timeout)
        return await self._get_scan_result(scan_id)

    async def _post_scan(
        self,
        workspace_ids: list[str],
        *,
        lineage: bool,
        datasource_details: bool,
        dataset_schema: bool,
        dataset_expressions: bool,
        get_artifact_users: bool,
    ) -> str:
        """Start a workspace scan and return the scan ID."""
        params = {
            "lineage": str(lineage).lower(),
            "datasourceDetails": str(datasource_details).lower(),
            "datasetSchema": str(dataset_schema).lower(),
            "datasetExpressions": str(dataset_expressions).lower(),
            "getArtifactUsers": str(get_artifact_users).lower(),
        }
        response: dict[str, object] = await self._client._request(
            "POST",
            f"{self._client.powerbi_base_url}/admin/workspaces/getInfo",
            params=params,
            json={"workspaces": workspace_ids},
        )
        return str(response["id"])

    async def _poll_scan(self, scan_id: str, *, timeout: int) -> None:
        """Poll scan status until success, failure, or timeout."""
        import time as _time

        deadline = _time.monotonic() + timeout
        while _time.monotonic() < deadline:
            try:
                status: dict[str, object] = await self._client._request(
                    "GET",
                    f"{self._client.powerbi_base_url}"
                    f"/admin/workspaces/scanStatus/{scan_id}",
                )
                st = status.get("status")
                if st == "Succeeded":
                    return
                if st == "Failed":
                    raise RuntimeError(f"Workspace scan {scan_id} failed")
            except Exception:
                pass  # Retry on transient errors
            await asyncio.sleep(2)
        raise RuntimeError(f"Workspace scan {scan_id} did not finish within {timeout}s")

    async def _get_scan_result(self, scan_id: str) -> list[WorkspaceScanResult]:
        """Fetch and parse the completed scan result."""
        payload: dict[str, object] = await self._client._request(
            "GET",
            f"{self._client.powerbi_base_url}/admin/workspaces/scanResult/{scan_id}",
        )
        workspaces_raw: list[dict[str, Any]] = payload.get("workspaces", [])  # type: ignore[assignment]
        return [WorkspaceScanResult.model_validate(ws) for ws in workspaces_raw]
