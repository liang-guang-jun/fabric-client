"""Token representation and provider abstraction."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fabric_client.auth.credentials import Credentials

logger = logging.getLogger(__name__)


@dataclass
class Token:
    """Represents an access token with expiration tracking."""

    access_token: str
    token_type: str = "Bearer"
    expires_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_expired(self, buffer_seconds: int = 300) -> bool:
        """Check if the token is expired or close to expiring.

        Args:
            buffer_seconds: Safety buffer in seconds (default 5 minutes).
        """
        return datetime.now(UTC) >= self.expires_at - timedelta(
            seconds=buffer_seconds
        )

    @property
    def authorization_header(self) -> dict[str, str]:
        """Return the Authorization header dict for HTTP requests."""
        return {"Authorization": f"{self.token_type} {self.access_token}"}


class TokenProvider:
    """Manages token acquisition and caching via MSAL."""

    def __init__(self, credentials: Credentials) -> None:
        """Initialize the token provider."""
        self._credentials = credentials
        self._token: Token | None = None

    async def get_token(self) -> Token:
        """Obtain a valid token, refreshing if necessary."""
        if self._token is None or self._token.is_expired:
            self._token = await self._acquire_token()
        return self._token

    async def _acquire_token(self) -> Token:
        """Acquire a new token from the identity provider."""
        raise NotImplementedError("Subclasses must implement _acquire_token")
