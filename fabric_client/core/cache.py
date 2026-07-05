"""Thread-safe in-memory TTL cache."""

from __future__ import annotations

import time
from collections import OrderedDict
from threading import RLock
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from fabric_client.logging.factory import LoggerFactory

T = TypeVar("T")


class _CacheEntry[T]:
    """A single cache entry with optional TTL."""

    __slots__ = ("expires_at", "value")

    def __init__(self, value: T, ttl: float | None = None) -> None:
        self.value = value
        self.expires_at = time.monotonic() + ttl if ttl is not None else None

    @property
    def expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.monotonic() >= self.expires_at


class Cache[T]:
    """A simple thread-safe in-memory cache with TTL support and LRU eviction.

    Used internally to cache API responses and reduce redundant network calls.
    """

    def __init__(
        self,
        maxsize: int = 128,
        default_ttl: float | None = 300.0,
        *,
        logger_factory: LoggerFactory | None = None,
    ) -> None:
        """Initialize cache with max size and default TTL."""
        from fabric_client.logging.factory import LoggerFactory as _LF  # noqa: N814

        self._maxsize = maxsize
        self._default_ttl = default_ttl
        self._store: OrderedDict[str, _CacheEntry[T]] = OrderedDict()
        self._lock = RLock()
        _factory = logger_factory or _LF.default()
        self._logger = _factory.get_logger(__name__)

    def get(self, key: str) -> T | None:
        """Retrieve a value from the cache. Returns None if missing or expired."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._logger.debug("Cache MISS key=%s", key)
                return None
            if entry.expired:
                self._logger.debug("Cache EXPIRED key=%s", key)
                del self._store[key]
                return None
            self._store.move_to_end(key)
            self._logger.debug("Cache HIT key=%s", key)
            return entry.value

    def set(self, key: str, value: T, ttl: float | None = None) -> None:
        """Store a value in the cache."""
        _effective_ttl = ttl if ttl is not None else self._default_ttl
        with self._lock:
            if key in self._store:
                self._logger.debug("Cache UPDATE key=%s ttl=%s", key, _effective_ttl)
                del self._store[key]
            elif len(self._store) >= self._maxsize:
                evicted = self._store.popitem(last=False)
                self._logger.debug(
                    "Cache EVICT key=%s (full, maxsize=%d)",
                    evicted[0],
                    self._maxsize,
                )
            self._store[key] = _CacheEntry(value, _effective_ttl)
            self._logger.debug("Cache SET key=%s ttl=%s", key, _effective_ttl)

    def invalidate(self, key: str) -> None:
        """Remove a specific key from the cache."""
        with self._lock:
            if key in self._store:
                self._store.pop(key, None)
                self._logger.debug("Cache INVALIDATE key=%s", key)

    def clear(self) -> None:
        """Remove all entries from the cache."""
        with self._lock:
            count = len(self._store)
            self._store.clear()
            self._logger.debug("Cache CLEAR (%d entries)", count)

    def __len__(self) -> int:
        """Return the number of entries in the cache."""
        with self._lock:
            return len(self._store)

    def __contains__(self, key: str) -> bool:
        """Check if a non-expired entry exists for the key."""
        return self.get(key) is not None
