"""Fabric SemanticModel model."""

from __future__ import annotations

import pydantic

from fabric_client.core.resource import Resource


class SemanticModelModel(pydantic.BaseModel):
    """Validated model for Fabric semantic model API responses."""

    id: str
    display_name: str = pydantic.Field(alias="displayName")
    description: str = ""
    type: str = "SemanticModel"
    workspace_id: str | None = pydantic.Field(
        default=None, alias="workspaceId"
    )

    model_config = pydantic.ConfigDict(populate_by_name=True)


class SemanticModel(Resource[SemanticModelModel]):
    """Represents a Fabric semantic model (previously known as a dataset)."""

    _api_path = "semanticModels"
    _model = SemanticModelModel
