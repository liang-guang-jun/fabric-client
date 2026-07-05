"""Main FabricClient entry point."""

from __future__ import annotations

import logging
from typing import Any

from fabric_client.apis.fabric.items import ItemsAPI
from fabric_client.apis.fabric.workspaces import WorkspacesAPI
from fabric_client.apis.powerbi.dataflows import DataflowsAPI
from fabric_client.apis.powerbi.datasets import DatasetsAPI
from fabric_client.apis.powerbi.reports import ReportsAPI
from fabric_client.auth.credentials import Credentials
from fabric_client.constants import (
    DEFAULT_TIMEOUT,
    FABRIC_API_BASE,
    POWERBI_API_BASE,
)
from fabric_client.core.cache import Cache
from fabric_client.core.http import AsyncHttpClient
from fabric_client.core.http_session import HttpSession
from fabric_client.session import Session

logger = logging.getLogger(__name__)


class FabricClient:
    """Main entry point for interacting with Microsoft Fabric and Power BI REST APIs.

    Usage::

        from fabric_client import FabricClient
        from fabric_client.auth.credentials import Credentials

        creds = Credentials.service_principal(
            tenant_id="...", client_id="...", client_secret="..."
        )
        client = FabricClient(creds)

        # List workspaces
        workspaces = await client.workspaces.list()
        async for ws in workspaces:
            print(ws.name)
    """

    def __init__(
        self,
        credentials: Credentials | Session | None = None,
        *,
        session: Session | None = None,
        base_url: str = FABRIC_API_BASE,
        powerbi_base_url: str = POWERBI_API_BASE,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 3,
        http_client: AsyncHttpClient | None = None,
    ) -> None:
        """Initialize the FabricClient."""
        if session is not None:
            self._session = session
        elif isinstance(credentials, Session):
            self._session = credentials
        elif isinstance(credentials, Credentials):
            self._session = Session(credentials)
        else:
            raise ValueError("Either credentials or session must be provided")

        self.base_url = base_url
        self.powerbi_base_url = powerbi_base_url
        self._cache: Cache[Any] = Cache()

        # Lazy-initialized API sub-clients
        self._workspaces: WorkspacesAPI | None = None
        self._items: ItemsAPI | None = None
        self._datasets: DatasetsAPI | None = None
        self._reports: ReportsAPI | None = None
        self._dataflows: DataflowsAPI | None = None

        # HTTP transport (handles auth injection, retry, error mapping)
        self._http_session = HttpSession(
            session=self._session,
            http_client=http_client,
            timeout=timeout,
            max_retries=max_retries,
        )

    # ------------------------------------------------------------------
    # Sub-clients (lazy)
    # ------------------------------------------------------------------

    @property
    def workspaces(self) -> WorkspacesAPI:
        """Access Fabric workspace operations."""
        if self._workspaces is None:
            self._workspaces = WorkspacesAPI(self)
        return self._workspaces

    @property
    def items(self) -> ItemsAPI:
        """Access generic Fabric item operations."""
        if self._items is None:
            self._items = ItemsAPI(self)
        return self._items

    @property
    def datasets(self) -> DatasetsAPI:
        """Access Power BI dataset operations."""
        if self._datasets is None:
            self._datasets = DatasetsAPI(self)
        return self._datasets

    @property
    def reports(self) -> ReportsAPI:
        """Access Power BI report operations."""
        if self._reports is None:
            self._reports = ReportsAPI(self)
        return self._reports

    @property
    def dataflows(self) -> DataflowsAPI:
        """Access Power BI dataflow operations."""
        if self._dataflows is None:
            self._dataflows = DataflowsAPI(self)
        return self._dataflows

    # ------------------------------------------------------------------
    # Session
    # ------------------------------------------------------------------

    @property
    def session(self) -> Session:
        """The session associated with this client."""
        return self._session

    @property
    def cache(self) -> Cache[Any]:
        """The client's response cache."""
        return self._cache

    # ------------------------------------------------------------------
    # HTTP (delegates to HttpSession)
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,  # noqa: ANN401
    ) -> Any:  # noqa: ANN401
        """Make an authenticated HTTP request to the Fabric / Power BI API."""
        return await self._http_session.request(
            method=method,
            url=url,
            params=params,
            json=json,
            headers=headers,
            **kwargs,
        )

    @property
    def http(self) -> HttpSession:
        """The underlying :class:`HttpSession` (transport layer)."""
        return self._http_session

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying HTTP session."""
        await self._http_session.close()

    async def __aenter__(self) -> FabricClient:
        """Enter the async context manager."""
        return self

    async def __aexit__(self, *args: Any) -> None:  # noqa: ANN401
        """Exit the async context manager, closing the session."""
        await self.close()
