"""Public API for the fabric-client package."""

from __future__ import annotations

import truststore

from fabric_client.auth.credentials import Credentials
from fabric_client.client import FabricClient
from fabric_client.exceptions import FabricClientError
from fabric_client.session import Session

# Inject system CA certificates for corporate/internal environments.
truststore.inject_into_ssl()

__version__ = "0.1.0"
__all__ = ["Credentials", "FabricClient", "FabricClientError", "Session"]
