"""Workspace-scoped API collections (datasets, reports, dataflows)."""

from __future__ import annotations

import logging
import re
from collections.abc import AsyncIterator, Coroutine, Generator
from typing import TYPE_CHECKING, Any

from fabric_client.apis.dataflow import (
    _inject_workspace_id,
    _normalize_gen2,
)
from fabric_client.apis.powerbi.dataflows import DataflowsAPI
from fabric_client.apis.powerbi.datasets import DatasetsAPI
from fabric_client.apis.powerbi.reports import ReportsAPI
from fabric_client.models.dataflow import Dataflow
from fabric_client.models.dataset import Dataset
from fabric_client.models.report import Report

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from fabric_client.models.workspace import Workspace


def _is_regex(pattern: str) -> bool:
    """Heuristic: treat as regex if it contains common regex metacharacters."""
    return any(c in pattern for c in r".*+?^${[(|")


class _ScopedList:
    """Base for scoped resource collections under a workspace.

    Provides ``await`` (→ list) and ``async for`` (→ iterate) semantics
    by delegating to the underlying global API with ``group_id`` fixed.

    Supports keyword filtering via ``__call__``::

        # All items
        datasets = await ws.datasets

        # Filter by keyword (substring match on id or name)
        filtered = await ws.datasets(keyword="Sample")

        # Filter by regex
        filtered = await ws.datasets(keyword=r".*日报.*")

    Results are **cached** after the first ``_resolve()`` call so
    subsequent ``await`` / ``async for`` on the same instance reuse
    the fetched data.
    """

    def __init__(self, workspace: Workspace) -> None:
        self._workspace = workspace
        self._cached: list[Any] | None = None

    @property
    def cached(self) -> list[Any] | None:
        """Return the cached items, or None if not yet fetched.

        Read-only — use ``await`` or ``async for`` to populate.
        """
        return self._cached

    @property
    def _client(self) -> Any:  # FabricClient  # noqa: ANN401
        return self._workspace._client

    @property
    def _group_id(self) -> str:
        return self._workspace.id

    # Subclasses override these -------------------------------------------------

    async def _list_raw(self) -> list[dict[str, object]]:
        raise NotImplementedError

    def _wrap(self, data: dict[str, object]) -> Any:  # noqa: ANN401
        raise NotImplementedError

    # Protocol ------------------------------------------------------------------

    async def _resolve(self) -> list[Any]:
        if self._cached is not None:
            return self._cached
        raw = await self._list_raw()
        self._cached = [self._wrap(item) for item in raw]
        return self._cached

    def __await__(self) -> Generator[Any, None, list[Any]]:
        return self._resolve().__await__()

    async def __aiter__(self) -> AsyncIterator[Any]:
        for item in await self._resolve():
            yield item

    # -- keyword filtering --------------------------------------------------

    def __call__(self, *, keyword: str) -> AwaitableList:
        """Return a filtered view of the collection.

        ``keyword`` is matched (case-insensitive) against each item's
        ``id`` and name (``name`` or ``display_name``).  Patterns
        containing regex metacharacters (``.*+?^$`` etc.) are treated
        as regular expressions; otherwise a plain substring match is
        used.

        Usage::

            await ws.datasets(keyword="Sample")
            await ws.datasets(keyword=r".*日报.*")
        """
        return AwaitableList(self._resolve(), keyword)

    @staticmethod
    def _filter_keyword(items: list[Any], keyword: str) -> list[Any]:
        """Filter *items* by *keyword* on id and name."""
        if _is_regex(keyword):
            try:
                pattern = re.compile(keyword, re.IGNORECASE)
            except re.error:
                # Fall back to substring match on invalid regex
                kw = keyword.lower()
                return [it for it in items if _match_substring(it, kw)]
            return [it for it in items if _match_regex(it, pattern)]
        kw = keyword.lower()
        return [it for it in items if _match_substring(it, kw)]


def _item_key_fields(item: Any) -> tuple[str, str]:  # noqa: ANN401
    """Return (id, name) strings from a resource item.

    Reads from the raw API data dict to avoid relying on Pydantic model
    attributes which may or may not be populated.
    """
    raw = getattr(item, "_data", {})
    iid = str(raw.get("id", raw.get("objectId", "")))
    name = str(raw.get("displayName") or raw.get("name") or "")
    return (iid, name)


def _match_substring(item: Any, kw: str) -> bool:  # noqa: ANN401
    """Case-insensitive substring match on id or name."""
    iid, name = _item_key_fields(item)
    return kw in iid.lower() or kw in name.lower()


def _match_regex(item: Any, pattern: re.Pattern[str]) -> bool:  # noqa: ANN401
    """Regex match on id or name."""
    iid, name = _item_key_fields(item)
    return bool(pattern.search(iid) or pattern.search(name))


class AwaitableList:
    """A lazy filtered list that supports ``await`` and ``async for``."""

    def __init__(self, coro: Coroutine[Any, Any, list[Any]], keyword: str) -> None:
        """Initialize with a coroutine and keyword filter."""
        self._coro = coro
        self._keyword = keyword
        self._result: list[Any] | None = None

    async def _compute(self) -> list[Any]:
        if self._result is None:
            items = await self._coro
            self._result = _ScopedList._filter_keyword(items, self._keyword)
        return self._result

    def __await__(self) -> Generator[Any, None, list[Any]]:
        """Await and return the filtered list."""
        return self._compute().__await__()

    async def __aiter__(self) -> AsyncIterator[Any]:
        """Iterate asynchronously over filtered items."""
        for item in await self._compute():
            yield item


class WorkspaceDatasets(_ScopedList):
    """Scoped Power BI datasets collection under a workspace.

    Usage::

        datasets = await ws.datasets          # list[Dataset]
        async for ds in ws.datasets: ...       # iterate
        ds = await ws.datasets.get(ds_id)     # single lookup
        await ws.datasets.refresh(ds_id)       # trigger refresh
    """

    async def _list_raw(self) -> list[dict[str, object]]:
        api = DatasetsAPI(self._client)
        return await api.list(group_id=self._group_id)

    def _wrap(self, data: dict[str, object]) -> Dataset:
        return Dataset(self._client, data)

    async def get(self, dataset_id: str) -> Dataset:
        """Get a single dataset by ID."""
        api = DatasetsAPI(self._client)
        raw = await api.get(dataset_id, group_id=self._group_id)
        return Dataset(self._client, raw)

    async def refresh(self, dataset_id: str) -> None:
        """Trigger a dataset refresh."""
        api = DatasetsAPI(self._client)
        await api.refresh(dataset_id, group_id=self._group_id)


class WorkspaceReports(_ScopedList):
    """Scoped Power BI reports collection under a workspace.

    Usage::

        reports = await ws.reports              # list[Report]
        async for r in ws.reports: ...           # iterate
        r = await ws.reports.get(report_id)     # single lookup
        buf = await ws.reports.export(r_id, "PDF")     # export
    """

    async def _list_raw(self) -> list[dict[str, object]]:
        api = ReportsAPI(self._client)
        return await api.list(group_id=self._group_id)

    def _wrap(self, data: dict[str, object]) -> Report:
        return Report(self._client, data)

    async def get(self, report_id: str) -> Report:
        """Get a single report by ID."""
        api = ReportsAPI(self._client)
        raw = await api.get(report_id, group_id=self._group_id)
        return Report(self._client, raw)

    async def export(self, report_id: str, file_format: str = "PDF") -> bytes:
        """Export a report to the specified format."""
        api = ReportsAPI(self._client)
        return await api.export(
            report_id, group_id=self._group_id, file_format=file_format
        )


class WorkspaceDataflows(_ScopedList):
    """Scoped Power BI + Fabric dataflows collection under a workspace.

    Merges Gen1 (Power BI) and Gen2 (Fabric) dataflows, deduplicating
    by id / objectId.

    Usage::

        dataflows = await ws.dataflows              # list[Dataflow]
        async for df in ws.dataflows: ...            # iterate
        df = await ws.dataflows.get(df_id)          # single lookup
        await ws.dataflows.refresh(df_id)            # trigger refresh
    """

    async def _list_raw(self) -> list[dict[str, object]]:
        from fabric_client.apis.fabric.items import ItemsAPI

        api = DataflowsAPI(self._client)
        gen1 = await api.list(group_id=self._group_id)
        _inject_workspace_id(gen1, self._group_id)
        gen1_ids: set[str] = {str(d.get("objectId", "")) for d in gen1}
        results: list[dict[str, object]] = list(gen1)

        # Gen2 — Fabric items of type "Dataflow"
        try:
            items_api = ItemsAPI(self._client)
            gen2 = await items_api.list(
                workspace_id=self._group_id, item_type="Dataflow"
            )
            for item in gen2:
                if str(item.get("id", "")) not in gen1_ids:
                    results.append(_normalize_gen2(item))
        except Exception:
            logger.debug(
                "Fabric Gen2 dataflow fetch failed for workspace %s",
                self._group_id,
                exc_info=True,
            )

        return results

    def _wrap(self, data: dict[str, object]) -> Dataflow:
        return Dataflow(self._client, data)

    async def get(self, dataflow_id: str) -> Dataflow:
        """Get a single dataflow by ID."""
        api = DataflowsAPI(self._client)
        raw = await api.get(dataflow_id, group_id=self._group_id)
        return Dataflow(self._client, raw)

    async def refresh(self, dataflow_id: str) -> None:
        """Trigger a dataflow refresh."""
        api = DataflowsAPI(self._client)
        await api.refresh(dataflow_id, group_id=self._group_id)
