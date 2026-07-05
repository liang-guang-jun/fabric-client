"""Public API for the fabric-client package."""

from __future__ import annotations

import truststore

from fabric_client.auth.credentials import Credentials
from fabric_client.client import FabricClient
from fabric_client.container import FabricContainer
from fabric_client.exceptions import FabricClientError
from fabric_client.logging.factory import LoggerFactory
from fabric_client.services.scan import scan
from fabric_client.session import Session

# Inject system CA certificates for corporate/internal environments.
truststore.inject_into_ssl()

__version__ = "0.1.0"
__all__ = [
    "Credentials",
    "FabricClient",
    "FabricClientError",
    "FabricContainer",
    "LoggerFactory",
    "Session",
    "scan",
]
