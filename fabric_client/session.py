"""Authentication session with automatic token refresh."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fabric_client.auth.msal import MSALTokenProvider
from fabric_client.auth.token import Token

if TYPE_CHECKING:
    from fabric_client.auth.credentials import Credentials

logger = logging.getLogger(__name__)


class Session:
    """Manages authentication and session state for the FabricClient.

    Holds the token provider and handles automatic token refresh.
    """

    def __init__(self, credentials: Credentials) -> None:
        """Initialize the session with credentials."""
        self._credentials = credentials
        self._token_provider = MSALTokenProvider(credentials)

    @property
    def credentials(self) -> Credentials:
        """The credentials used for this session."""
        return self._credentials

    async def get_token(self) -> Token:
        """Obtain a valid access token, refreshing if necessary."""
        return await self._token_provider.get_token()

    async def get_authorization_header(self) -> dict[str, str]:
        """Return the Authorization header for HTTP requests."""
        token = await self.get_token()
        return token.authorization_header
