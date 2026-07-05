"""MSAL-based token acquisition."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import msal  # type: ignore[import-untyped]

from fabric_client.auth.token import Token, TokenProvider

if TYPE_CHECKING:
    from fabric_client.auth.credentials import Credentials

logger = logging.getLogger(__name__)

# Default scopes for Fabric / Power BI REST APIs
DEFAULT_SCOPES = ["https://analysis.windows.net/powerbi/api/.default"]


class MSALTokenProvider(TokenProvider):
    """Token provider backed by the MSAL library."""

    def __init__(
        self, credentials: Credentials, scopes: list[str] | None = None
    ) -> None:
        """Initialize with credentials and optional scopes."""
        super().__init__(credentials)
        self._scopes = scopes or DEFAULT_SCOPES
        self._app = self._build_app(credentials)

    @staticmethod
    def _build_app(
        credentials: Credentials,
    ) -> msal.ConfidentialClientApplication:
        """Build an MSAL confidential client application."""
        return msal.ConfidentialClientApplication(
            client_id=credentials.client_id,
            client_credential=credentials.client_secret,
            authority=f"https://login.microsoftonline.com/{credentials.tenant_id}",
        )

    async def _acquire_token(self) -> Token:
        """Acquire a token silently or via client credentials flow."""
        result = self._app.acquire_token_silent(
            scopes=self._scopes,
            account=None,
        )
        if result is None:
            result = self._app.acquire_token_for_client(scopes=self._scopes)

        if "access_token" not in result:
            error = result.get(
                "error_description", result.get("error", "Unknown error")
            )
            raise RuntimeError(f"Failed to acquire token: {error}")

        expires_in = result.get("expires_in", 3600)
        return Token(
            access_token=result["access_token"],
            token_type=result.get("token_type", "Bearer"),
            expires_at=datetime.now(UTC) + timedelta(seconds=expires_in),
        )
