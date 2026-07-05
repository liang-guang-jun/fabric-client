"""Custom logging formatter for fabric-client.

Renders log records with: timestamp, level, module name, and
optional duration/extra context.
"""

from __future__ import annotations

import logging
import time
from typing import ClassVar


class FabricFormatter(logging.Formatter):
    """Human-readable formatter with optional elapsed-time tracking.

    Output format::

        [DEBUG   ] fabric_client.client  GET /workspaces → 200 (234ms)
        [INFO    ] http_session  Retrying (attempt 2/3) after 429
    """

    # Lightweight color/style markers (no hard dependency on colorama)
    LEVEL_COLORS: ClassVar[dict[str, str]] = {
        "DEBUG": "\033[36m",  # cyan
        "INFO": "\033[32m",  # green
        "WARNING": "\033[33m",  # yellow
        "ERROR": "\033[31m",  # red
        "CRITICAL": "\033[1;31m",  # bold red
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def __init__(
        self,
        *,
        fmt: str | None = None,
        datefmt: str = "%Y-%m-%d %H:%M:%S",
        use_colors: bool = True,
    ) -> None:
        """Initialize the formatter.

        Args:
            fmt: Custom ``logging`` format string (defaults to built-in).
            datefmt: ``strftime`` format for timestamps.
            use_colors: Whether to include ANSI color codes.
        """
        super().__init__(
            fmt=fmt
            or "%(asctime)s.%(msecs)03d [%(levelname)-8s] %(name)s  %(message)s",
            datefmt=datefmt,
        )
        self._use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        """Add ANSI colours and optional duration before rendering."""
        record.__dict__.setdefault("msecs", int(record.relativeCreated) % 1000)
        if self._use_colors:
            color = self.LEVEL_COLORS.get(record.levelname, "")
            record.levelname = f"{color}{record.levelname}{self.RESET}"
            record.name = f"{self.BOLD}{record.name}{self.RESET}"
        return super().format(record)

    def formatTime(  # noqa: N802
        self, record: logging.LogRecord, datefmt: str | None = None
    ) -> str:
        """Render the timestamp using ``time.strftime``."""
        ct = time.localtime(record.created)
        return time.strftime(datefmt or self.default_time_format, ct)
