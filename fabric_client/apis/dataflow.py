"""Unified dataflow API: merges Power BI Gen1 and Fabric Gen2 dataflows."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fabric_client.apis.fabric.items import ItemsAPI
from fabric_client.apis.powerbi.dataflows import DataflowsAPI

if TYPE_CHECKING:
    from fabric_client.client import FabricClient

logger = logging.getLogger(__name__)


def _normalize_gen2(item: dict[str, object]) -> dict[str, object]:
    """Normalize a Fabric Gen2 dataflow item for compatibility with Gen1.

    - Set ``generation`` to 2 (Fabric returns 0 for items)
    - Set ``id`` from ``objectId`` if missing
    - Ensure ``displayName`` becomes ``name`` for the model alias
    """
    item = dict(item)
    item["generation"] = 2
    if "id" not in item and "objectId" in item:
        item["id"] = item["objectId"]
    if "displayName" in item and "name" not in item:
        item["name"] = item["displayName"]
    return item


def _inject_workspace_id(
    items: list[dict[str, object]], workspace_id: str
) -> list[dict[str, object]]:
    """Add ``workspaceId`` to each Gen1 item that lacks it."""
    for d in items:
        if "workspaceId" not in d:
            d["workspaceId"] = workspace_id
    return items


class MergedDataflowsAPI:
    """Aggregates dataflows from both Power BI (Gen1) and Fabric (Gen2).

    The Power BI API returns Gen1 dataflows; the Fabric Items API returns
    Gen2 dataflows.  This class fetches from both sources and merges the
    results, deduplicating by id / objectId.
    """

    def __init__(self, client: FabricClient) -> None:
        """Initialize with the shared client."""
        self._client = client
        self._pbi = DataflowsAPI(client)
        self._fabric_items = ItemsAPI(client)

    async def list(
        self,
        group_id: str | None = None,
        **params: Any,  # noqa: ANN401
    ) -> list[dict[str, object]]:
        """List Gen1 and Gen2 dataflows, deduplicated.

        When *group_id* is provided, both sources are scoped to that
        workspace.  Without it, only the Power BI (Gen1) global list is
        returned (Fabric Gen2 requires a workspace context).
        """
        results: list[dict[str, object]] = []

        # Gen1 — Power BI API (works without or with group_id)
        gen1 = await self._pbi.list(group_id=group_id, **params)
        if group_id:
            _inject_workspace_id(gen1, group_id)
        gen1_ids: set[str] = {str(d.get("objectId", "")) for d in gen1}
        results.extend(gen1)

        # Gen2 — Fabric Items API (requires workspace / group_id)
        if group_id:
            try:
                gen2 = await self._fabric_items.list(
                    workspace_id=group_id, item_type="Dataflow"
                )
                for item in gen2:
                    if str(item.get("id", "")) not in gen1_ids:
                        results.append(_normalize_gen2(item))
            except Exception:
                logger.debug(
                    "Fabric Gen2 dataflow fetch failed for workspace %s",
                    group_id,
                    exc_info=True,
                )

        return results
