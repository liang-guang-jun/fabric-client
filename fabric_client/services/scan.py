"""Admin workspace scan service and scan() entry point."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterable
from typing import TYPE_CHECKING, Any

from fabric_client.models.scan import WorkspaceScanResult
from fabric_client.models.workspace import Workspace

if TYPE_CHECKING:
    from fabric_client.client import FabricClient

_SCAN_BATCH_SIZE = 100


async def scan(
    workspaces: Iterable[Workspace],
    *,
    lineage: bool = True,
    datasource_details: bool = True,
    dataset_schema: bool = True,
    dataset_expressions: bool = True,
    get_artifact_users: bool = True,
    timeout: int = 7200,
    scan_ttl: float | None = 300.0,
) -> AsyncIterator[Workspace]:
    """Scan workspaces and yield them with ``.scanned`` data injected.

    Results are cached on the client keyed by workspace ID.  Subsequent
    calls skip the API for cached workspaces (until *scan_ttl* expires).

    Usage::

        async for ws in scan(await client.workspaces):
            print(ws.scanned.state)

        # Force re-scan
        async for ws in scan(workspaces, scan_ttl=0):
            ...
    """
    ws_list = list(workspaces)
    if not ws_list:
        return

    client: FabricClient = ws_list[0]._client
    logger = client._logger_factory.get_logger(__name__)

    # Split into cached (fresh) and uncached (need API call)
    cached: dict[str, WorkspaceScanResult] = {}
    uncached: list[str] = []
    for ws in ws_list:
        entry: WorkspaceScanResult | None = client._scan_cache.get(ws.id)
        if entry is not None:
            cached[ws.id] = entry
        else:
            uncached.append(ws.id)

    if uncached:
        logger.info(
            "Starting scan for %d workspace(s) (%d cached, %d uncached): %s",
            len(ws_list),
            len(cached),
            len(uncached),
            uncached[:5] if len(uncached) <= 5 else [*uncached[:5], "…"],
        )
        service = WorkspaceScanService(client)
        fresh = await service.scan(
            uncached,
            lineage=lineage,
            datasource_details=datasource_details,
            dataset_schema=dataset_schema,
            dataset_expressions=dataset_expressions,
            get_artifact_users=get_artifact_users,
            timeout=timeout,
        )
        for r in fresh:
            cached[r.id] = r
            client._scan_cache.set(r.id, r, ttl=scan_ttl)
        logger.info("Scan completed: %d workspace(s) enriched", len(fresh))
    else:
        logger.info(
            "All %d workspace(s) served from cache (ttl=%.0fs)",
            len(ws_list),
            scan_ttl,
        )

    for ws in ws_list:
        result = cached.get(ws.id)
        if result is not None:
            ws._scan_cache = {ws.id: result}  # type: ignore[attr-defined]
        yield ws


class WorkspaceScanService:
    """Orchestrate admin workspace scans (low-level)."""

    def __init__(self, client: FabricClient) -> None:
        """Initialize with a client."""
        self._client = client
        self._logger = client._logger_factory.get_logger(__name__)

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

        self._logger.info(
            "Scanning %d workspace(s) in %d batch(es)",
            len(workspace_ids),
            (len(workspace_ids) + _SCAN_BATCH_SIZE - 1) // _SCAN_BATCH_SIZE,
        )
        _start = __import__("time").monotonic()
        batches = [
            workspace_ids[i : i + _SCAN_BATCH_SIZE]
            for i in range(0, len(workspace_ids), _SCAN_BATCH_SIZE)
        ]

        if len(batches) == 1:
            result = await self._scan_batch(
                workspace_ids=batches[0],
                lineage=lineage,
                datasource_details=datasource_details,
                dataset_schema=dataset_schema,
                dataset_expressions=dataset_expressions,
                get_artifact_users=get_artifact_users,
                timeout=timeout,
            )
            self._logger.info(
                "Single-batch scan completed in %dms",
                int((__import__("time").monotonic() - _start) * 1000),
            )
            return result

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
        self._logger.info(
            "Multi-batch scan (%d batches) completed in %dms, %d results",
            len(batches),
            int((__import__("time").monotonic() - _start) * 1000),
            len(merged),
        )
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
