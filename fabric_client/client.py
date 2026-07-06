"""Main FabricClient entry point."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fabric_client.apis.dataflow import MergedDataflowsAPI
from fabric_client.apis.fabric.items import ItemsAPI
from fabric_client.apis.fabric.workspaces import WorkspacesAPI
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

if TYPE_CHECKING:
    from fabric_client.logging.factory import LoggerFactory


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
        http_session: HttpSession | None = None,
        logger_factory: LoggerFactory | None = None,
    ) -> None:
        """Initialize the FabricClient.

        Args:
            credentials: Credentials or Session for authentication.
            session: Pre-built :class:`Session` (overrides ``credentials``).
            base_url: Fabric REST API base URL.
            powerbi_base_url: Power BI REST API base URL.
            timeout: Default HTTP request timeout in seconds.
            max_retries: Maximum retry attempts for transient failures.
            http_client: Plugable HTTP backend (defaults to aiohttp).
            http_session: Pre-built :class:`HttpSession` (for DI; overrides
                ``http_client``, ``timeout``, and ``max_retries``).
            logger_factory: Shared :class:`LoggerFactory` for the client and
                all sub-components.
        """
        # Resolve session
        if session is not None:
            self._session = session
        elif isinstance(credentials, Session):
            self._session = credentials
        elif isinstance(credentials, Credentials):
            self._session = Session(credentials)
        else:
            raise ValueError("Either credentials or session must be provided")

        # Logger factory (shared across all sub-components)
        from fabric_client.logging.factory import LoggerFactory as _LF  # noqa: N814

        self._logger_factory: LoggerFactory = logger_factory or _LF.default()
        self._logger = self._logger_factory.get_logger(__name__)

        self.base_url = base_url
        self.powerbi_base_url = powerbi_base_url
        self._cache: Cache[Any] = Cache(logger_factory=self._logger_factory)

        # Scan result cache (keyed by workspace ID, TTL = 5 min)
        self._scan_cache: Cache[Any] = Cache(
            maxsize=1024,
            default_ttl=300.0,
            logger_factory=self._logger_factory,
        )

        # Lazy-initialized API sub-clients
        self._workspaces: WorkspacesAPI | None = None
        self._items: ItemsAPI | None = None
        self._datasets: DatasetsAPI | None = None
        self._reports: ReportsAPI | None = None
        self._dataflows: MergedDataflowsAPI | None = None

        # HTTP transport (handles auth injection, retry, error mapping)
        if http_session is not None:
            self._http_session = http_session
        else:
            self._http_session = HttpSession(
                session=self._session,
                http_client=http_client,
                timeout=timeout,
                max_retries=max_retries,
                logger_factory=self._logger_factory,
            )

        self._logger.info(
            "FabricClient initialised (base=%s, powerbi=%s, timeout=%.0fs)",
            self.base_url,
            self.powerbi_base_url,
            timeout if http_session is None else 0,
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
    def dataflows(self) -> MergedDataflowsAPI:
        """Access merged dataflow operations (Power BI Gen1 + Fabric Gen2)."""
        if self._dataflows is None:
            self._dataflows = MergedDataflowsAPI(self)
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

    @property
    def logger_factory(self) -> LoggerFactory:
        """The shared :class:`LoggerFactory` used by all components."""
        return self._logger_factory

    def set_log_level(self, level: int | str) -> None:
        """Dynamically change the log level for all components.

        Accepts integer levels (``logging.DEBUG``) or string names
        (``"DEBUG"``, ``"INFO"``, ``"WARNING"``, ``"ERROR"``).

        Usage::

            client.set_log_level("DEBUG")   # verbose
            client.set_log_level("WARNING") # quiet
        """
        import logging as _logging

        if isinstance(level, str):
            level = _logging._nameToLevel.get(level.upper(), _logging.INFO)
        self._logger_factory.level = level
        self._logger.info("Log level changed to %s", _logging.getLevelName(level))

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
        self._logger.debug("Closing FabricClient")
        await self._http_session.close()
        self._logger.debug("FabricClient closed")

    async def __aenter__(self) -> FabricClient:
        """Enter the async context manager."""
        self._logger.debug("Entering FabricClient context")
        return self

    async def __aexit__(self, *args: Any) -> None:  # noqa: ANN401
        """Exit the async context manager, closing the session."""
        await self.close()
