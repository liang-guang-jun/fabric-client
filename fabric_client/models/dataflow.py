"""Power BI Dataflow model."""

from __future__ import annotations

from typing import Any

import pydantic

from fabric_client.core.resource import Resource


class DataflowModel(pydantic.BaseModel):
    """Validated model for Power BI dataflow API responses."""

    id: str = pydantic.Field(
        validation_alias=pydantic.AliasChoices("id", "objectId")
    )
    name: str = ""
    description: str = ""
    model_url: str | None = pydantic.Field(default=None, alias="modelUrl")
    configured_by: str | None = pydantic.Field(
        default=None, alias="configuredBy"
    )
    modified_by: str | None = pydantic.Field(default=None, alias="modifiedBy")
    users: list[Any] = pydantic.Field(default_factory=list)
    generation: int = 0

    model_config = pydantic.ConfigDict(populate_by_name=True)


class Dataflow(Resource[DataflowModel]):
    """Represents a Power BI dataflow."""

    _api_path = "dataflows"
    _model = DataflowModel
