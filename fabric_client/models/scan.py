"""Admin workspace scan result models."""

from __future__ import annotations

import pydantic


class _ScanModel(pydantic.BaseModel):
    """Base model for scan payloads with extra fields allowed."""

    model_config = pydantic.ConfigDict(extra="allow", populate_by_name=True)


class ScanDatasource(_ScanModel):
    """Datasource attached to a dataset or dataflow."""

    datasource_id: str | None = pydantic.Field(default=None, alias="datasourceId")
    datasource_type: str | None = pydantic.Field(default=None, alias="datasourceType")
    gateway_id: str | None = pydantic.Field(default=None, alias="gatewayId")
    connection_details: dict[str, object] = pydantic.Field(
        default_factory=dict, alias="connectionDetails"
    )


class ScanArtifactUser(_ScanModel):
    """User / access control entry on a scanned artifact."""

    display_name: str | None = pydantic.Field(default=None, alias="displayName")
    email_address: str | None = pydantic.Field(default=None, alias="emailAddress")
    identifier: str | None = None
    graph_id: str | None = pydantic.Field(default=None, alias="graphId")
    principal_type: str | None = pydantic.Field(default=None, alias="principalType")
    user_type: str | None = pydantic.Field(default=None, alias="userType")


class ScanExpression(_ScanModel):
    """Power Query / DAX expression from a scanned artifact."""

    name: str = ""
    expression: str = ""


class ScanDataflow(_ScanModel):
    """Dataflow metadata from a scan result."""

    object_id: str = pydantic.Field(alias="objectId")
    name: str = ""
    description: str | None = None
    generation: int | None = None
    configured_by: str | None = pydantic.Field(default=None, alias="configuredBy")
    modified_by: str | None = pydantic.Field(default=None, alias="modifiedBy")
    modified_date_time: str | None = pydantic.Field(
        default=None, alias="modifiedDateTime"
    )
    datasource_usages: list[dict[str, object]] = pydantic.Field(
        default_factory=list, alias="datasourceUsages"
    )
    users: list[ScanArtifactUser] = pydantic.Field(default_factory=list)
    expressions: list[ScanExpression] = pydantic.Field(default_factory=list)


class ScanTableSource(_ScanModel):
    """Source expression for a single scanned table."""

    expression: str = ""


class ScanTable(_ScanModel):
    """Table metadata from a scan result."""

    name: str = ""
    is_hidden: bool | None = pydantic.Field(default=None, alias="isHidden")
    storage_mode: str | None = pydantic.Field(default=None, alias="storageMode")
    columns: list[dict[str, object]] = pydantic.Field(default_factory=list)
    measures: list[dict[str, object]] = pydantic.Field(default_factory=list)
    source: list[ScanTableSource] = pydantic.Field(default_factory=list)


class ScanDataset(_ScanModel):
    """Dataset / semantic model metadata from a scan result."""

    id: str = ""
    name: str = ""
    configured_by: str | None = pydantic.Field(default=None, alias="configuredBy")
    target_storage_mode: str | None = pydantic.Field(
        default=None, alias="targetStorageMode"
    )
    created_date: str | None = pydantic.Field(default=None, alias="createdDate")
    is_effective_identity_required: bool | None = pydantic.Field(
        default=None, alias="isEffectiveIdentityRequired"
    )
    is_effective_identity_roles_required: bool | None = pydantic.Field(
        default=None, alias="isEffectiveIdentityRolesRequired"
    )
    expressions: list[ScanExpression] = pydantic.Field(default_factory=list)
    datasource_details: list[ScanDatasource] = pydantic.Field(
        default_factory=list, alias="datasourceDetails"
    )
    tables: list[ScanTable] = pydantic.Field(default_factory=list)
    upstream_dataflows: list[dict[str, object]] = pydantic.Field(
        default_factory=list, alias="upstreamDataflows"
    )
    users: list[ScanArtifactUser] = pydantic.Field(default_factory=list)


class ScanReport(_ScanModel):
    """Report metadata from a scan result."""

    id: str = ""
    name: str = ""
    report_type: str | None = pydantic.Field(default=None, alias="reportType")
    dataset_id: str | None = pydantic.Field(default=None, alias="datasetId")
    dataset_workspace_id: str | None = pydantic.Field(
        default=None, alias="datasetWorkspaceId"
    )
    created_date_time: str | None = pydantic.Field(
        default=None, alias="createdDateTime"
    )
    modified_date_time: str | None = pydantic.Field(
        default=None, alias="modifiedDateTime"
    )
    created_by: str | None = pydantic.Field(default=None, alias="createdBy")
    modified_by: str | None = pydantic.Field(default=None, alias="modifiedBy")
    users: list[ScanArtifactUser] = pydantic.Field(default_factory=list)


class WorkspaceScanResult(_ScanModel):
    """Per-workspace scan payload."""

    id: str = ""
    name: str = ""
    type: str | None = None
    state: str | None = None
    is_on_dedicated_capacity: bool | None = pydantic.Field(
        default=None, alias="isOnDedicatedCapacity"
    )
    capacity_id: str | None = pydantic.Field(default=None, alias="capacityId")
    reports: list[ScanReport] = pydantic.Field(default_factory=list)
    datasets: list[ScanDataset] = pydantic.Field(default_factory=list)
    dataflows: list[ScanDataflow] = pydantic.Field(default_factory=list)
    users: list[ScanArtifactUser] = pydantic.Field(default_factory=list)
