"""Authentication credential types."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum


class CredentialType(Enum):
    """Supported authentication credential types."""

    SERVICE_PRINCIPAL = "service_principal"
    USER_DELEGATED = "user_delegated"
    MANAGED_IDENTITY = "managed_identity"


@dataclass
class Credentials:
    """Authentication credentials for connecting to Microsoft Fabric / Power BI."""

    credential_type: CredentialType
    tenant_id: str
    client_id: str
    client_secret: str | None = None
    username: str | None = None
    password: str | None = None

    @classmethod
    def service_principal(
        cls, tenant_id: str, client_id: str, client_secret: str
    ) -> Credentials:
        """Create service principal credentials."""
        return cls(
            credential_type=CredentialType.SERVICE_PRINCIPAL,
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )

    @classmethod
    def user_delegated(
        cls, tenant_id: str, client_id: str, username: str, password: str
    ) -> Credentials:
        """Create user-delegated (ROPC) credentials."""
        return cls(
            credential_type=CredentialType.USER_DELEGATED,
            tenant_id=tenant_id,
            client_id=client_id,
            username=username,
            password=password,
        )

    @classmethod
    def env(cls) -> Credentials:
        """Create service principal credentials from environment variables.

        Reads the following variables:

        - ``FABRIC_CLI_TENANT_ID``
        - ``FABRIC_CLI_CLIENT_ID``
        - ``FABRIC_CLI_CLIENT_SECRET``

        Raises:
            ValueError: If any required variable is not set.
        """
        required = {
            "FABRIC_CLI_TENANT_ID": "tenant_id",
            "FABRIC_CLI_CLIENT_ID": "client_id",
            "FABRIC_CLI_CLIENT_SECRET": "client_secret",
        }
        missing = [env_var for env_var in required if not os.getenv(env_var)]
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        return cls.service_principal(
            tenant_id=os.environ["FABRIC_CLI_TENANT_ID"],
            client_id=os.environ["FABRIC_CLI_CLIENT_ID"],
            client_secret=os.environ["FABRIC_CLI_CLIENT_SECRET"],
        )
