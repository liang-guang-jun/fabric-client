"""Dependency-injection container for fabric-client.

Provides a declarative :class:`FabricContainer` that wires together
:class:`~fabric_client.client.FabricClient`, its HTTP transport,
and the :class:`~fabric_client.logging.factory.LoggerFactory`.

Usage::

    from dependency_injector import providers
    from fabric_client.container import FabricContainer

    container = FabricContainer()
    container.config.from_dict({
        "credentials": creds,
        "log": {"level": "DEBUG"},
        "http": {"timeout": 30},
    })
    client = container.client()
    async with client:
        ...
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from dependency_injector import containers, providers

from fabric_client.auth.credentials import Credentials
from fabric_client.constants import DEFAULT_TIMEOUT
from fabric_client.core.http_aiohttp import AioHttpClient
from fabric_client.core.http_session import HttpSession
from fabric_client.logging.factory import LoggerFactory
from fabric_client.session import Session

if TYPE_CHECKING:
    from fabric_client.client import FabricClient


def _build_client(
    session: Session,
    http_session: HttpSession,
    logger_factory: LoggerFactory,
    config: Any,  # noqa: ANN401
) -> FabricClient:
    """Factory that assembles a :class:`FabricClient` from DI providers."""
    from fabric_client.client import FabricClient

    kwargs: dict[str, Any] = {
        "session": session,
        "http_session": http_session,
        "logger_factory": logger_factory,
    }
    # Only override defaults when config values are explicitly set
    fabric_base = _safe_config(config, "fabric", "base_url")
    if fabric_base is not None:
        kwargs["base_url"] = fabric_base
    powerbi_base = _safe_config(config, "powerbi", "base_url")
    if powerbi_base is not None:
        kwargs["powerbi_base_url"] = powerbi_base

    return FabricClient(**kwargs)


def _safe_config(config: Any, *keys: str) -> Any | None:  # noqa: ANN401
    """Walk nested config keys, returning None if any level is unset."""
    node: Any = config
    for key in keys:
        if not hasattr(node, key):
            return None
        node = getattr(node, key)
    value = node() if callable(node) else node
    return value if value is not None else None


def _log_level_from_config(config: Any) -> int:  # noqa: ANN401
    """Extract log level from config, defaulting to INFO."""
    if hasattr(config, "log") and hasattr(config.log, "level"):
        raw = config.log.level()
        if raw is not None:
            return int(raw)
    return logging.INFO


class FabricContainer(containers.DeclarativeContainer):
    """Dependency-injection container for the Fabric client stack.

    All ``config`` keys are optional and fall back to sensible defaults.
    """

    config = providers.Configuration()

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    logger_factory = providers.Singleton(
        LoggerFactory,
        level=_log_level_from_config(config),
    )

    # ------------------------------------------------------------------
    # Auth / session
    # ------------------------------------------------------------------

    credentials: providers.Provider[Credentials] = providers.Dependency()

    session = providers.Singleton(
        Session,
        credentials=credentials,
    )

    # ------------------------------------------------------------------
    # HTTP transport
    # ------------------------------------------------------------------

    http_client = providers.Singleton(AioHttpClient)

    timeout = providers.Callable(
        lambda config: _safe_config(config, "http", "timeout") or DEFAULT_TIMEOUT,
        config=config,
    )

    max_retries = providers.Callable(
        lambda config: _safe_config(config, "http", "max_retries") or 3,
        config=config,
    )

    http_session = providers.Singleton(
        HttpSession,
        session=session,
        http_client=http_client,
        timeout=timeout,
        max_retries=max_retries,
        logger_factory=logger_factory,
    )

    # ------------------------------------------------------------------
    # Top-level client
    # ------------------------------------------------------------------

    client: providers.Provider[FabricClient] = providers.Singleton(
        _build_client,
        session=session,
        http_session=http_session,
        logger_factory=logger_factory,
        config=config,
    )
