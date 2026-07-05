"""Fabric Workspace model."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import pydantic

from fabric_client.core.collection import LazyCollection
from fabric_client.core.resource import Resource
from fabric_client.models.scan import WorkspaceScanResult

if TYPE_CHECKING:
    from fabric_client.apis.scoped import (
        WorkspaceDataflows,
        WorkspaceDatasets,
        WorkspaceReports,
    )
    from fabric_client.client import FabricClient


class WorkspaceModel(pydantic.BaseModel):
    """Validated model for Fabric workspace API responses."""

    id: str
    display_name: str = pydantic.Field(alias="displayName")
    description: str = ""
    capacity_id: str | None = pydantic.Field(default=None, alias="capacityId")
    capacity_region: str | None = pydantic.Field(default=None, alias="capacityRegion")
    domain_id: str | None = pydantic.Field(default=None, alias="domainId")
    type: str = "Workspace"

    model_config = pydantic.ConfigDict(populate_by_name=True)


class Workspace(Resource[WorkspaceModel]):
    """Represents a Microsoft Fabric workspace."""

    _api_path = "workspaces"
    _model = WorkspaceModel

    # -- scoped sub-APIs (lazy, cached) -----------------------------------

    _datasets: WorkspaceDatasets | None = None
    _reports: WorkspaceReports | None = None
    _dataflows: WorkspaceDataflows | None = None

    @property
    def datasets(self) -> WorkspaceDatasets:
        """Scoped datasets collection."""
        if self._datasets is None:
            from fabric_client.apis.scoped import WorkspaceDatasets

            self._datasets = WorkspaceDatasets(self)
        return self._datasets

    @property
    def reports(self) -> WorkspaceReports:
        """Scoped reports collection."""
        if self._reports is None:
            from fabric_client.apis.scoped import WorkspaceReports

            self._reports = WorkspaceReports(self)
        return self._reports

    @property
    def dataflows(self) -> WorkspaceDataflows:
        """Scoped dataflows collection."""
        if self._dataflows is None:
            from fabric_client.apis.scoped import WorkspaceDataflows

            self._dataflows = WorkspaceDataflows(self)
        return self._dataflows

    # -- bulk fetch --------------------------------------------------------

    async def prefetch(self) -> None:
        """Fetch datasets, reports, and dataflows in parallel.

        Subsequent ``await ws.datasets`` / ``async for`` calls return
        immediately from cache.
        """
        self._logger.info("Prefetching scoped collections for workspace=%s", self.id)
        import time as _time

        _start = _time.monotonic()
        await asyncio.gather(
            self.datasets._resolve(),
            self.reports._resolve(),
            self.dataflows._resolve(),
        )
        self._logger.debug(
            "Prefetched workspace=%s scoped collections in %dms",
            self.id,
            int((_time.monotonic() - _start) * 1000),
        )

    # -- scan --------------------------------------------------------------

    @property
    def scanned(self) -> WorkspaceScanResult:
        """Admin scan result, populated after ``client.workspaces.scanned``."""
        cache: dict[str, WorkspaceScanResult] = getattr(self, "_scan_cache", {})
        result = cache.get(self.id)
        if result is None:
            self._logger.warning("No scan result for workspace=%s", self.id)
            raise RuntimeError("No scan result. Iterate via scan() first.")
        self._logger.debug("Returning cached scan result for workspace=%s", self.id)
        return result

    # -- lifecycle ---------------------------------------------------------

    async def refresh(self) -> None:
        """Refresh workspace metadata from the API."""
        return

    @staticmethod
    async def list(
        client: FabricClient,
        **params: Any,  # noqa: ANN401
    ) -> LazyCollection[Workspace]:
        """List all workspaces accessible by the authenticated principal."""
        from fabric_client.apis.fabric.workspaces import WorkspacesAPI

        api = WorkspacesAPI(client)
        return await api.list(**params)
