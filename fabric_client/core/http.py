"""Abstract HTTP client interface and response wrapper."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class HttpResponse:
    """Normalised HTTP response returned by all backends."""

    status_code: int
    headers: dict[str, str]
    content: bytes
    content_type: str = ""

    def json(self) -> Any:  # noqa: ANN401
        """Parse the response body as JSON."""
        import json as _json

        return _json.loads(self.content)

    def text(self) -> str:
        """Return the response body as a UTF-8 string."""
        return self.content.decode("utf-8", errors="replace")


class AsyncHttpClient(ABC):
    """Abstract async HTTP client backend.

    Implementations exist for ``aiohttp`` (default) and ``httpx``.
    """

    @abstractmethod
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
        """Perform an HTTP request and return a normalised response."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Release underlying resources (sessions, connection pools)."""
        ...
