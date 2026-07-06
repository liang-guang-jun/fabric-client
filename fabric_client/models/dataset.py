"""Power BI Dataset model."""

from __future__ import annotations

from collections.abc import AsyncIterator, Generator
from typing import TYPE_CHECKING, Any

import pydantic

from fabric_client.core.collection import _AsyncListProxy
from fabric_client.core.resource import Resource
from fabric_client.models.scan import ScanTable

if TYPE_CHECKING:
    from fabric_client.services.power_query import PowerQuerySection


class DatasetModel(pydantic.BaseModel):
    """Validated model for Power BI dataset API responses."""

    id: str = pydantic.Field(validation_alias=pydantic.AliasChoices("id", "objectId"))
    name: str = ""
    configured_by: str | None = pydantic.Field(default=None, alias="configuredBy")
    web_url: str | None = pydantic.Field(default=None, alias="webUrl")
    is_refreshable: bool = pydantic.Field(default=False, alias="isRefreshable")
    is_effective_identity_required: bool = pydantic.Field(
        default=False, alias="isEffectiveIdentityRequired"
    )
    is_effective_identity_roles_required: bool = pydantic.Field(
        default=False, alias="isEffectiveIdentityRolesRequired"
    )
    is_on_prem_gateway_required: bool = pydantic.Field(
        default=False, alias="isOnPremGatewayRequired"
    )
    add_rows_api_enabled: bool = pydantic.Field(
        default=False, alias="addRowsAPIEnabled"
    )
    target_storage_mode: str | None = pydantic.Field(
        default=None, alias="targetStorageMode"
    )
    created_date: str | None = pydantic.Field(default=None, alias="createdDate")
    create_report_embed_url: str | None = pydantic.Field(
        default=None, alias="createReportEmbedURL"
    )
    qna_embed_url: str | None = pydantic.Field(default=None, alias="qnaEmbedURL")
    upstream_datasets: list[Any] = pydantic.Field(
        default_factory=list, alias="upstreamDatasets"
    )
    users: list[Any] = pydantic.Field(default_factory=list)
    query_scale_out_settings: dict[str, Any] | None = pydantic.Field(
        default=None, alias="queryScaleOutSettings"
    )

    model_config = pydantic.ConfigDict(populate_by_name=True)


class DatasetRefresh(pydantic.BaseModel):
    """A single dataset refresh history entry."""

    request_id: str = pydantic.Field(alias="requestId")
    id: int = 0
    refresh_type: str | None = pydantic.Field(default=None, alias="refreshType")
    start_time: str | None = pydantic.Field(default=None, alias="startTime")
    end_time: str | None = pydantic.Field(default=None, alias="endTime")
    status: str = "Unknown"
    refresh_attempts: list[dict[str, object]] = pydantic.Field(
        default_factory=list, alias="refreshAttempts"
    )
    workspace_id: str | None = None
    dataset_id: str | None = None

    model_config = pydantic.ConfigDict(populate_by_name=True)


class RefreshSchedule(pydantic.BaseModel):
    """Refresh schedule for an import-mode dataset."""

    days: list[str] = pydantic.Field(default_factory=list)
    times: list[str] = pydantic.Field(default_factory=list)
    enabled: bool = False
    local_time_zone_id: str | None = pydantic.Field(
        default=None,
        alias="localTimeZoneId",
    )
    notify_option: str | None = pydantic.Field(
        default=None,
        alias="notifyOption",
    )

    model_config = pydantic.ConfigDict(populate_by_name=True)


class Dataset(Resource[DatasetModel]):
    """Represents a Power BI / Fabric dataset (semantic model storage).

    Supports lazy Power Query source extraction via scan data::

        async for ws in client.workspaces.scanned:
            async for ds in ws.datasets:
                async for s in ds.scanned_queries:
                    print(s.name, s.expression)
    """

    _api_path = "datasets"
    _model = DatasetModel

    @property
    def scanned_queries(self) -> _ScannedDatasetQueries:
        """Lazy loader for table PQ sources from scan data."""
        return _ScannedDatasetQueries(self)

    @property
    def queries(self) -> _ScannedDatasetQueries:
        """Compatible alias for scanned_queries."""
        return _ScannedDatasetQueries(self)

    @property
    def tables(self) -> _ScannedDatasetTables:
        """Lazy loader for table metadata from scan data (``ScanTable``)."""
        return _ScannedDatasetTables(self)

    @property
    def schedule(self) -> _AsyncListProxy[RefreshSchedule]:
        """Refresh schedule (``await`` or ``async for``).

        Returns empty for non-refreshable datasets.
        """
        if not self.pydantic.is_refreshable:

            async def _empty() -> list[RefreshSchedule]:
                return []

            return _AsyncListProxy(_empty)

        from fabric_client.apis.powerbi.datasets import DatasetsAPI

        api = DatasetsAPI(self._client)
        ws_id = self.workspace.id if self.workspace else ""

        async def _fetch() -> list[RefreshSchedule]:
            s = await api.get_refresh_schedule(self.id, group_id=ws_id)
            return [s]

        return _AsyncListProxy(_fetch)

    # -- refresh -----------------------------------------------------------

    async def refresh(  # type: ignore[override]
        self,
        *,
        force: bool = False,
        wait: bool = False,
        timeout: int = 7200,
    ) -> list[DatasetRefresh] | None:
        """Trigger a dataset refresh.

        Args:
            force: Cancel active refresh before starting.
            wait: Poll until completion.
            timeout: Max seconds to wait.

        Returns:
            Refresh list if ``wait=True``, else ``None``.
        """
        self._logger.info(
            "Triggering dataset refresh id=%s force=%s wait=%s",
            self.id,
            force,
            wait,
        )
        from fabric_client.apis.powerbi.datasets import DatasetsAPI

        api = DatasetsAPI(self._client)
        ws_id = self.workspace.id if self.workspace else None
        result = await api.refresh(
            self.id,
            group_id=ws_id,
            force=force,
            wait=wait,
            timeout=timeout,
        )
        self._logger.info("Dataset refresh completed id=%s", self.id)
        return result

    @property
    def refreshes(self) -> _AsyncListProxy[DatasetRefresh]:
        """List refresh history (``await`` or ``async for``).

        Returns empty for non-refreshable datasets (e.g. usage metrics).
        """
        if not self.pydantic.is_refreshable:

            async def _empty() -> list[DatasetRefresh]:
                return []

            return _AsyncListProxy(_empty)

        from fabric_client.apis.powerbi.datasets import DatasetsAPI

        api = DatasetsAPI(self._client)
        ws_id = self.workspace.id if self.workspace else ""

        async def _fetch() -> list[DatasetRefresh]:
            return await api.list_refreshes(ws_id, self.id)

        return _AsyncListProxy(_fetch)

    async def cancel_refresh(self, refresh_id: str) -> None:
        """Cancel an in-progress dataset refresh."""
        from fabric_client.apis.powerbi.datasets import DatasetsAPI

        api = DatasetsAPI(self._client)
        ws_id = self.workspace.id if self.workspace else ""
        await api.cancel_refresh(ws_id, self.id, refresh_id)


class _ScannedDatasetTables:
    """Lazy loader for dataset table metadata from scan data.

    Returns :class:`ScanTable` objects (no additional API calls).
    """

    def __init__(self, dataset: Dataset) -> None:
        self._ds = dataset
        self._tables: list[ScanTable] | None = None

    async def _resolve(self) -> list[ScanTable]:
        if self._tables is not None:
            return self._tables
        self._tables = []

        ws = self._ds.workspace
        if ws is None:
            return self._tables

        try:
            scanned = ws.scanned
        except (RuntimeError, AttributeError):
            return self._tables

        for scan_ds in scanned.datasets:
            if scan_ds.id != self._ds.id:
                continue
            self._tables = list(scan_ds.tables)
            break

        return self._tables

    def __await__(self) -> Generator[Any, None, list[ScanTable]]:
        return self._resolve().__await__()

    async def __aiter__(self) -> AsyncIterator[ScanTable]:
        for t in await self._resolve():
            yield t


class _ScannedDatasetQueries:
    """Lazy loader for dataset table Power Query expressions.

    Reads from the scan-enriched workspace data (no additional API calls).
    """

    def __init__(self, dataset: Dataset) -> None:
        self._ds = dataset
        self._sources: list[PowerQuerySection] | None = None

    async def _resolve(self) -> list[PowerQuerySection]:
        from fabric_client.services.power_query import PowerQuerySection

        if self._sources is not None:
            return self._sources
        self._sources = []

        # Get scan data via workspace back-reference
        ws = self._ds.workspace
        if ws is None:
            return self._sources

        try:
            scanned = ws.scanned
        except (RuntimeError, AttributeError):
            return self._sources

        # Find matching scan dataset and extract table sources
        for scan_ds in scanned.datasets:
            if scan_ds.id != self._ds.id:
                continue
            for table in scan_ds.tables:
                if table.source:
                    name = table.name
                    expr = table.source[0].expression
                    self._sources.append(
                        PowerQuerySection(
                            name=name,
                            expression=expr,
                            workspace_id=ws.id,
                            refreshable_type="dataset",
                            refreshable_id=self._ds.id,
                        )
                    )
            break

        return self._sources

    def __await__(self) -> Generator[Any, None, list[PowerQuerySection]]:
        return self._resolve().__await__()

    async def __aiter__(self) -> AsyncIterator[PowerQuerySection]:
        for s in await self._resolve():
            yield s
