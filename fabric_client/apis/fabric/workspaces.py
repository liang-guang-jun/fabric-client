"""Fabric workspace API operations."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Generator
from typing import TYPE_CHECKING, Any, cast

from fabric_client.core.collection import LazyCollection
from fabric_client.core.endpoint import Endpoint
from fabric_client.core.paginator import Paginator
from fabric_client.models.scan import WorkspaceScanResult
from fabric_client.models.workspace import Workspace

if TYPE_CHECKING:
    from fabric_client.client import FabricClient

logger = logging.getLogger(__name__)


class WorkspacesAPI:
    """API client for Microsoft Fabric workspace operations.

    Supports both ``await`` and ``async for`` syntax for listing::

        # Await — returns a plain list
        workspaces = await client.workspaces

        # Async iteration — streams from a LazyCollection
        async for ws in client.workspaces:
            print(ws.name)
    """

    def __init__(self, client: FabricClient) -> None:
        """Initialize the Workspaces API client."""
        self._client = client

    # -- protocol: await / async for ------------------------------------

    async def _resolve(self, **params: Any) -> list[Workspace]:  # noqa: ANN401
        """Resolve the default listing into a concrete list."""
        collection = await self.list(**params)
        return await collection.all()

    def __await__(self) -> Generator[Any, None, list[Workspace]]:
        """Await the default listing and return a concrete list."""
        return self._resolve().__await__()

    async def __aiter__(self) -> AsyncIterator[Workspace]:
        """Iterate asynchronously over workspaces."""
        collection = await self.list()
        async for item in collection:
            yield item

    @property
    def scanned(self) -> ScannedWorkspaces:
        """Iterate workspaces with admin scan results injected.

        Usage::

            async for ws in client.workspaces.scanned:
                print(ws.scanned.dataflows)  # scan-enriched metadata
        """
        return ScannedWorkspaces(self)

    # -- API methods ----------------------------------------------------

    async def get(self, workspace_id: str) -> Workspace:
        """Get a workspace by ID."""
        endpoint = Endpoint("GET", "/workspaces/{workspaceId}")
        url = endpoint.build_url(self._client.base_url, workspaceId=workspace_id)
        data = await self._client._request("GET", url)
        return Workspace(self._client, data)

    async def list(self, **params: Any) -> LazyCollection[Workspace]:  # noqa: ANN401
        """List workspaces accessible by the authenticated principal.

        Performs a single GET request and returns all items in the response.
        Use :meth:`list_paginated` if you need to traverse large result sets
        with continuation tokens.
        """
        endpoint = Endpoint("GET", "/workspaces")

        async def _fetcher(**kwargs: Any) -> list[dict[str, object]]:  # noqa: ANN401
            url = endpoint.build_url(self._client.base_url)
            response = await self._client._request("GET", url, params=kwargs)
            return cast("list[dict[str, object]]", response.get("value", []))

        return LazyCollection(
            client=self._client,
            fetcher=_fetcher,
            factory=Workspace._from_data,
            fetcher_kwargs=params,
        )

    async def list_paginated(self, **params: Any) -> LazyCollection[Workspace]:  # noqa: ANN401
        """List workspaces with full pagination support.

        Traverses all pages via continuation tokens. Useful for large
        result sets — use :meth:`list` for most cases.
        """
        endpoint = Endpoint("GET", "/workspaces")

        async def _fetcher(**kwargs: Any) -> list[dict[str, object]]:  # noqa: ANN401
            url = endpoint.build_url(self._client.base_url)
            paginator = Paginator[dict[str, object]](
                fetcher=lambda **p: self._client._request("GET", url, params=p),
                page_delay=0.5,
                **kwargs,
            )
            return await paginator.collect_all()

        return LazyCollection(
            client=self._client,
            fetcher=_fetcher,
            factory=Workspace._from_data,
            fetcher_kwargs=params,
        )

    async def create(
        self,
        name: str,
        description: str = "",
        capacity_id: str | None = None,
    ) -> Workspace:
        """Create a new workspace."""
        endpoint = Endpoint("POST", "/workspaces")
        url = endpoint.build_url(self._client.base_url)
        body: dict[str, Any] = {
            "displayName": name,
            "description": description,
        }
        if capacity_id:
            body["capacityId"] = capacity_id
        data = await self._client._request("POST", url, json=body)
        return Workspace(self._client, data)

    async def update(self, workspace_id: str, **updates: Any) -> Workspace:  # noqa: ANN401
        """Update an existing workspace."""
        endpoint = Endpoint("PATCH", "/workspaces/{workspaceId}")
        url = endpoint.build_url(self._client.base_url, workspaceId=workspace_id)
        data = await self._client._request("PATCH", url, json=updates)
        return Workspace(self._client, data)

    async def delete(self, workspace_id: str) -> None:
        """Delete a workspace."""
        endpoint = Endpoint("DELETE", "/workspaces/{workspaceId}")
        url = endpoint.build_url(self._client.base_url, workspaceId=workspace_id)
        await self._client._request("DELETE", url)


class ScannedWorkspaces:
    """Iterate workspaces with admin scan results lazily injected.

    Kicks off a background scan when iteration begins and attaches
    results to each :class:`Workspace` via ``.scanned``.

    Usage::

        async for ws in client.workspaces.scanned:
            print(ws.scanned.state)
            async for df in ws.dataflows:
                print(df.workspace.scanned.state)
    """

    def __init__(self, api: WorkspacesAPI) -> None:
        """Initialize with the workspace API."""
        self._api = api

    async def __aiter__(self) -> AsyncIterator[Workspace]:
        """List workspaces, await scan, then yield enriched results."""
        from fabric_client.services.scan import WorkspaceScanService

        workspaces = await self._api._resolve()
        if not workspaces:
            return

        ws_ids = [ws.id for ws in workspaces]
        scan_service = WorkspaceScanService(self._api._client)

        # Run scan and wait for completion
        results = await scan_service.scan(ws_ids)
        scan_cache: dict[str, WorkspaceScanResult] = {r.id: r for r in results}

        for ws in workspaces:
            ws._scan_cache = scan_cache  # type: ignore[attr-defined]
            yield ws
