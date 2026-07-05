"""HTTP backend implementation using httpx."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from fabric_client.core.http import AsyncHttpClient, HttpResponse

logger = logging.getLogger(__name__)


class HttpxClient(AsyncHttpClient):
    """Async HTTP client backed by ``httpx``."""

    def __init__(self) -> None:
        """Initialize the httpx client."""
        self._client: httpx.AsyncClient | None = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                limits=httpx.Limits(
                    max_connections=20, max_keepalive_connections=5
                ),
            )
        return self._client

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
        """Perform an HTTP request via httpx."""
        client = await self._ensure_client()
        response = await client.request(
            method=method,
            url=url,
            params=params,
            json=json,
            headers=headers,
            timeout=timeout,
        )
        return HttpResponse(
            status_code=response.status_code,
            headers=dict(response.headers),
            content=response.content,
            content_type=response.headers.get("content-type", ""),
        )

    async def close(self) -> None:
        """Close the httpx client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
