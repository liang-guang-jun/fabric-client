"""Power BI Report model."""

from __future__ import annotations

from typing import Any

import pydantic

from fabric_client.core.collection import _AsyncListProxy
from fabric_client.core.resource import Resource


class ReportModel(pydantic.BaseModel):
    """Validated model for Power BI report API responses."""

    id: str = pydantic.Field(validation_alias=pydantic.AliasChoices("id", "objectId"))
    name: str = ""
    report_type: str = pydantic.Field(default="PowerBIReport", alias="reportType")
    web_url: str | None = pydantic.Field(default=None, alias="webUrl")
    embed_url: str | None = pydantic.Field(default=None, alias="embedUrl")
    dataset_id: str | None = pydantic.Field(default=None, alias="datasetId")
    app_id: str | None = pydantic.Field(default=None, alias="appId")
    format: str | None = None
    is_from_pbix: bool = pydantic.Field(default=False, alias="isFromPbix")
    is_owned_by_me: bool = pydantic.Field(default=False, alias="isOwnedByMe")
    dataset_workspace_id: str | None = pydantic.Field(
        default=None, alias="datasetWorkspaceId"
    )
    users: list[Any] = pydantic.Field(default_factory=list)
    subscriptions: list[Any] = pydantic.Field(default_factory=list)

    model_config = pydantic.ConfigDict(populate_by_name=True)


class ReportPage(pydantic.BaseModel):
    """A single page within a Power BI report."""

    display_name: str = pydantic.Field(default="", alias="displayName")
    name: str = ""
    order: int = 0

    model_config = pydantic.ConfigDict(populate_by_name=True)


class Report(Resource[ReportModel]):
    """Represents a Power BI / Fabric report."""

    _api_path = "reports"
    _model = ReportModel

    @property
    def pages(self) -> _AsyncListProxy[ReportPage]:
        """Report pages (``await`` or ``async for``)."""
        from fabric_client.apis.powerbi.reports import ReportsAPI

        api = ReportsAPI(self._client)
        ws_id = self.workspace.id if self.workspace else ""

        async def _fetch() -> list[ReportPage]:
            return await api.get_pages(self.id, group_id=ws_id)

        return _AsyncListProxy(_fetch)
