"""HTTP transport layer (auth, retry, error mapping)."""

from __future__ import annotations

import logging
import random
import re
from typing import Any

import tenacity

from fabric_client.constants import DEFAULT_TIMEOUT
from fabric_client.core.http import AsyncHttpClient, HttpResponse
from fabric_client.exceptions import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    FabricClientError,
    NotFoundError,
    RateLimitError,
)
from fabric_client.session import Session

logger = logging.getLogger(__name__)


class HttpSession:
    """Encapsulates all HTTP transport logic: backend, auth, retry, error mapping.

    Used internally by :class:`FabricClient` — not intended for direct
    instantiation by end users.
    """

    def __init__(
        self,
        session: Session,
        *,
        http_client: AsyncHttpClient | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 3,
    ) -> None:
        """Initialize the HTTP session."""
        self._session = session
        self._timeout = timeout
        self._max_retries = max_retries
        self._http: AsyncHttpClient | None = http_client

    # ------------------------------------------------------------------
    # Backend
    # ------------------------------------------------------------------

    async def _ensure_http(self) -> AsyncHttpClient:
        """Return the HTTP backend, defaulting to aiohttp if not set."""
        if self._http is None:
            from fabric_client.core.http_aiohttp import AioHttpClient

            self._http = AioHttpClient()
        return self._http

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,  # noqa: ANN401
    ) -> Any:  # noqa: ANN401
        """Perform an authenticated HTTP request with retry and error mapping."""
        auth_header = await self._session.get_authorization_header()
        merged_headers = {**auth_header, **(headers or {})}
        http = await self._ensure_http()

        retrier = tenacity.AsyncRetrying(
            retry=self._retry_predicate,
            stop=tenacity.stop_after_attempt(self._max_retries),
            wait=self._compute_wait,
            before_sleep=tenacity.before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )

        async for attempt in retrier:
            with attempt:
                response = await http.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json,
                    headers=merged_headers,
                    timeout=self._timeout,
                )
                return self._handle_response(response)

        raise FabricClientError("Request failed")

    # ------------------------------------------------------------------
    # Response handling
    # ------------------------------------------------------------------

    @staticmethod
    def _handle_response(response: HttpResponse) -> Any:  # noqa: ANN401
        """Map HTTP response to result or exception."""
        status = response.status_code

        if 200 <= status < 300:
            if response.content_type.startswith("application/json"):
                return response.json()
            return response.content

        try:
            error_body = response.json()
            error_msg = error_body.get("error", {}).get(
                "message", response.text()
            )
        except Exception:
            error_msg = response.text()

        if status == 401:
            raise AuthenticationError(f"Authentication failed: {error_msg}")
        elif status == 403:
            raise AuthorizationError(f"Access denied: {error_msg}")
        elif status == 404:
            raise NotFoundError(f"Resource not found: {error_msg}")
        elif status == 409:
            raise ConflictError(f"Conflict: {error_msg}")
        elif status == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(
                f"Rate limit exceeded: {error_msg}",
                retry_after=int(retry_after) if retry_after else None,
            )
        else:
            raise APIError(
                f"API error ({status}): {error_msg}",
                status_code=status,
                response_body=response.text(),
            )

    # ------------------------------------------------------------------
    # Retry logic (tenacity callbacks)
    # ------------------------------------------------------------------

    @staticmethod
    def _retry_predicate(retry_state: tenacity.RetryCallState) -> bool:
        """Return True for exceptions that should trigger a retry."""
        exc: BaseException | None = None
        if retry_state.outcome and retry_state.outcome.failed:
            exc = retry_state.outcome.exception()
        if isinstance(exc, RateLimitError):
            return True
        return isinstance(exc, (OSError, TimeoutError))

    @staticmethod
    def _compute_wait(retry_state: tenacity.RetryCallState) -> float:
        """Compute the wait time before the next retry.

        Uses the server-specified delay from ``RateLimitError`` when
        available, falling back to exponential jitter.
        """
        exc: BaseException | None = None
        if retry_state.outcome and retry_state.outcome.failed:
            exc = retry_state.outcome.exception()
        if isinstance(exc, RateLimitError):
            return HttpSession._parse_retry_delay(exc)
        base: float = min(2.0 ** (retry_state.attempt_number - 1), 60.0)
        return base + random.uniform(0.0, base * 0.5)

    @staticmethod
    def _parse_retry_delay(error: RateLimitError) -> float:
        """Extract retry delay in seconds from a RateLimitError."""
        if error.retry_after is not None:
            return float(error.retry_after)
        match = re.search(r"blocked until:\s*(.+?)\s*\(UTC\)", str(error))
        if match:
            try:
                from datetime import UTC, datetime

                dt = datetime.strptime(
                    match.group(1).strip(), "%m/%d/%Y %I:%M:%S %p"
                )
                dt = dt.replace(tzinfo=UTC)
                delay = (dt - datetime.now(UTC)).total_seconds()
                return max(delay, 1.0)
            except ValueError:
                pass
        return 10.0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying HTTP backend."""
        if self._http is not None:
            await self._http.close()
            self._http = None
