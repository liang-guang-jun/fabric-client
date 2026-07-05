"""Power BI Dataflow model."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pydantic

from fabric_client.core.collection import _AsyncListProxy
from fabric_client.core.resource import Resource

if TYPE_CHECKING:
    from fabric_client.services.power_query import PowerQueryParser


class DataflowModel(pydantic.BaseModel):
    """Validated model for Power BI (Gen1) and Fabric (Gen2) dataflows."""

    id: str = pydantic.Field(validation_alias=pydantic.AliasChoices("id", "objectId"))
    name: str = pydantic.Field(
        default="",
        validation_alias=pydantic.AliasChoices("name", "displayName"),
    )
    description: str = ""
    model_url: str | None = pydantic.Field(default=None, alias="modelUrl")
    configured_by: str | None = pydantic.Field(default=None, alias="configuredBy")
    modified_by: str | None = pydantic.Field(default=None, alias="modifiedBy")
    users: list[Any] = pydantic.Field(default_factory=list)
    generation: int = 0
    type: str = ""
    display_name: str = pydantic.Field(default="", alias="displayName")
    workspace_id: str | None = pydantic.Field(default=None, alias="workspaceId")

    model_config = pydantic.ConfigDict(populate_by_name=True)


class DataflowTransaction(pydantic.BaseModel):
    """A single dataflow refresh transaction."""

    id: str
    refresh_type: str | None = pydantic.Field(default=None, alias="refreshType")
    start_time: str | None = pydantic.Field(default=None, alias="startTime")
    end_time: str | None = pydantic.Field(default=None, alias="endTime")
    status: str = "Unknown"
    workspace_id: str | None = None
    dataflow_id: str | None = None

    model_config = pydantic.ConfigDict(populate_by_name=True)


class Dataflow(Resource[DataflowModel]):
    """Represents a Power BI dataflow.

    Supports lazy Power Query source extraction::

        async for source in df.queries:
            print(source.name, source.expression)
    """

    _api_path = "dataflows"
    _model = DataflowModel

    @property
    def queries(self) -> PowerQueryParser:
        """Lazy loader for Power Query shared sources."""
        from fabric_client.services.power_query import PowerQueryParser

        return PowerQueryParser(self)

    # -- refresh / transactions (Gen1 only) --------------------------------

    async def refresh(  # type: ignore[override]
        self,
        *,
        force: bool = False,
        wait: bool = False,
        timeout: int = 7200,
    ) -> list[DataflowTransaction] | None:
        """Trigger a dataflow refresh (Gen1).

        Args:
            force: Cancel active transaction before starting.
            wait: Poll until completion.
            timeout: Max seconds to wait.

        Returns:
            Transaction list if ``wait=True``, else ``None``.
        """
        from fabric_client.apis.powerbi.dataflows import DataflowsAPI

        api = DataflowsAPI(self._client)
        ws_id = self.pydantic.workspace_id
        return await api.refresh(
            self.id,
            group_id=ws_id,
            force=force,
            wait=wait,
            timeout=timeout,
        )

    @property
    def transactions(self) -> _AsyncListProxy[DataflowTransaction]:
        """List refresh transactions — Gen1 only (Gen2 returns empty)."""
        from fabric_client.apis.powerbi.dataflows import DataflowsAPI

        ws_id = self.pydantic.workspace_id or ""

        if self.pydantic.generation == 2:

            async def _empty() -> list[DataflowTransaction]:
                return []

            return _AsyncListProxy(_empty)

        api = DataflowsAPI(self._client)

        async def _fetch() -> list[DataflowTransaction]:
            return await api.list_transactions(ws_id, self.id)

        return _AsyncListProxy(_fetch)

    async def cancel_transaction(self, transaction_id: str) -> None:
        """Cancel an active dataflow transaction (Gen1)."""
        from fabric_client.apis.powerbi.dataflows import DataflowsAPI

        api = DataflowsAPI(self._client)
        ws_id = self.pydantic.workspace_id or ""
        await api.cancel_transaction(ws_id, transaction_id)
