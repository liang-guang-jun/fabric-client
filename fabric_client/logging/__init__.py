"""Logging infrastructure for fabric-client.

Provides a :class:`LoggerFactory` that creates structured loggers
with consistent formatting, and a :class:`FabricFormatter` for
pretty-printed console output.
"""

from __future__ import annotations

from fabric_client.logging.factory import LoggerFactory

__all__ = ["LoggerFactory"]
