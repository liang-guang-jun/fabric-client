"""Exception hierarchy for fabric-client."""

from __future__ import annotations


class FabricClientError(Exception):
    """Base exception for all fabric-client errors."""


class AuthenticationError(FabricClientError):
    """Raised when authentication fails."""


class AuthorizationError(FabricClientError):
    """Raised when the authenticated principal lacks required permissions."""


class NotFoundError(FabricClientError):
    """Raised when a requested resource is not found (HTTP 404)."""


class ConflictError(FabricClientError):
    """Raised when a conflict occurs (HTTP 409)."""


class RateLimitError(FabricClientError):
    """Raised when API rate limits are exceeded (HTTP 429)."""

    def __init__(self, message: str, retry_after: int | None = None) -> None:
        """Initialize with optional retry-after delay."""
        super().__init__(message)
        self.retry_after = retry_after


class ValidationError(FabricClientError):
    """Raised when input validation fails."""


class APIError(FabricClientError):
    """Raised when the API returns an unexpected error."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
    ) -> None:
        """Initialize with status code and response body."""
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class TimeoutError(FabricClientError):
    """Raised when a request times out."""
