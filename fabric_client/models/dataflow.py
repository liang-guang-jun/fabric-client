"""Power BI Dataflow model."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pydantic

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


class Dataflow(Resource[DataflowModel]):
    """Represents a Power BI dataflow.

    Supports lazy Power Query source extraction::

        async for source in df.sources:
            print(source.name, source.expression)
    """

    _api_path = "dataflows"
    _model = DataflowModel

    @property
    def sources(self) -> PowerQueryParser:
        """Lazy loader for Power Query ``shared`` sources.

        Automatically dispatches to the correct API based on
        ``generation`` (1 → Power BI admin, 2 → Fabric definition).

        Usage::

            sources = await df.sources           # list[DataflowSource]
            async for s in df.sources: ...        # iterate
        """
        from fabric_client.services.power_query import PowerQueryParser

        return PowerQueryParser(self)
