"""Power BI Dataset model."""

from __future__ import annotations

from typing import Any

import pydantic

from fabric_client.core.resource import Resource


class DatasetModel(pydantic.BaseModel):
    """Validated model for Power BI dataset API responses."""

    id: str = pydantic.Field(
        validation_alias=pydantic.AliasChoices("id", "objectId")
    )
    name: str = ""
    configured_by: str | None = pydantic.Field(
        default=None, alias="configuredBy"
    )
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
    created_date: str | None = pydantic.Field(
        default=None, alias="createdDate"
    )
    create_report_embed_url: str | None = pydantic.Field(
        default=None, alias="createReportEmbedURL"
    )
    qna_embed_url: str | None = pydantic.Field(
        default=None, alias="qnaEmbedURL"
    )
    upstream_datasets: list[Any] = pydantic.Field(
        default_factory=list, alias="upstreamDatasets"
    )
    users: list[Any] = pydantic.Field(default_factory=list)
    query_scale_out_settings: dict[str, Any] | None = pydantic.Field(
        default=None, alias="queryScaleOutSettings"
    )

    model_config = pydantic.ConfigDict(populate_by_name=True)


class Dataset(Resource[DatasetModel]):
    """Represents a Power BI / Fabric dataset (semantic model storage)."""

    _api_path = "datasets"
    _model = DatasetModel
