"""Thread-safe in-memory TTL cache."""

from __future__ import annotations

import time
from collections import OrderedDict
from threading import RLock
from typing import TypeVar

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
        self, maxsize: int = 128, default_ttl: float | None = 300.0
    ) -> None:
        """Initialize cache with max size and default TTL."""
        self._maxsize = maxsize
        self._default_ttl = default_ttl
        self._store: OrderedDict[str, _CacheEntry[T]] = OrderedDict()
        self._lock = RLock()

    def get(self, key: str) -> T | None:
        """Retrieve a value from the cache. Returns None if missing or expired."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.expired:
                del self._store[key]
                return None
            self._store.move_to_end(key)
            return entry.value

    def set(self, key: str, value: T, ttl: float | None = None) -> None:
        """Store a value in the cache."""
        with self._lock:
            if key in self._store:
                del self._store[key]
            elif len(self._store) >= self._maxsize:
                self._store.popitem(last=False)
            self._store[key] = _CacheEntry(
                value, ttl if ttl is not None else self._default_ttl
            )

    def invalidate(self, key: str) -> None:
        """Remove a specific key from the cache."""
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        """Remove all entries from the cache."""
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        """Return the number of entries in the cache."""
        with self._lock:
            return len(self._store)

    def __contains__(self, key: str) -> bool:
        """Check if a non-expired entry exists for the key."""
        return self.get(key) is not None
