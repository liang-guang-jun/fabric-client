"""HTTP backend implementation using aiohttp."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from fabric_client.core.http import AsyncHttpClient, HttpResponse

logger = logging.getLogger(__name__)


class AioHttpClient(AsyncHttpClient):
    """Async HTTP client backed by ``aiohttp`` (the default)."""

    def __init__(self) -> None:
        """Initialize the aiohttp client."""
        self._session: aiohttp.ClientSession | None = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(limit=20, limit_per_host=5)
            timeout = aiohttp.ClientTimeout(total=60)
            self._session = aiohttp.ClientSession(
                connector=connector, timeout=timeout
            )
        return self._session

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> HttpResponse:
        """Perform an HTTP request via aiohttp."""
        session = await self._ensure_session()

        kw: dict[str, Any] = {"headers": headers}
        if params:
            kw["params"] = params
        if json is not None:
            kw["json"] = json

        client_timeout = (
            aiohttp.ClientTimeout(total=timeout)
            if timeout
            else aiohttp.ClientTimeout(total=60)
        )

        async with session.request(
            method, url, timeout=client_timeout, **kw
        ) as resp:
            content = await resp.read()
            return HttpResponse(
                status_code=resp.status,
                headers=dict(resp.headers),
                content=content,
                content_type=resp.content_type,
            )

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
