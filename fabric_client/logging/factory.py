"""LoggerFactory — centralised logger creation with custom formatting."""

from __future__ import annotations

import logging
import sys
from typing import ClassVar


class LoggerFactory:
    """Creates and caches :class:`logging.Logger` instances.

    Provides consistent formatter and handler configuration.
    """

    _default_instance: ClassVar[LoggerFactory | None] = None

    def __init__(
        self,
        *,
        level: int = logging.INFO,
        use_colors: bool = True,
        stream: logging.Handler | None = None,
    ) -> None:
        """Initialize the factory.

        Args:
            level: Default log level for all created loggers.
            use_colors: Whether to emit ANSI colour codes.
            stream: Optional pre-configured handler (creates a
                ``StreamHandler(sys.stderr)`` if omitted).
        """
        from fabric_client.logging.formatter import FabricFormatter

        self._level = level
        self._use_colors = use_colors
        self._formatter = FabricFormatter(use_colors=use_colors)
        self._handler = stream or logging.StreamHandler(sys.stderr)
        self._handler.setFormatter(self._formatter)
        self._loggers: dict[str, logging.Logger] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_logger(self, name: str) -> logging.Logger:
        """Return (or create and cache) a logger for *name*.

        The returned logger propagates to the root logger (``False``),
        has its level set to the factory default, and uses the shared
        formatted handler.
        """
        if name not in self._loggers:
            logger = logging.getLogger(name)
            logger.propagate = False
            logger.setLevel(self._level)
            # Avoid adding the same handler twice if the factory
            # is re-used across multiple get_logger calls.
            if self._handler not in logger.handlers:
                logger.addHandler(self._handler)
            self._loggers[name] = logger
        return self._loggers[name]

    @property
    def level(self) -> int:
        """The default log level assigned to new loggers."""
        return self._level

    @level.setter
    def level(self, value: int) -> None:
        """Update the level on all cached loggers."""
        self._level = value
        for lg in self._loggers.values():
            lg.setLevel(value)

    @classmethod
    def default(cls) -> LoggerFactory:
        """Return a shared singleton ``LoggerFactory``.

        Useful so that callers who don't receive an explicit factory
        can still obtain a consistent logger.
        """
        if cls._default_instance is None:
            cls._default_instance = cls()
        return cls._default_instance

    def reset(self) -> None:
        """Remove all cached loggers (useful in tests)."""
        self._loggers.clear()
