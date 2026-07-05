"""Lazy-loaded paginated collection."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Awaitable, Callable, Coroutine, Generator
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from fabric_client.client import FabricClient

T = TypeVar("T")


class LazyCollection[T]:
    """A lazily-loaded collection of API resources with optional pagination.

    Items are fetched on demand and cached locally.
    """

    def __init__(
        self,
        client: FabricClient,
        fetcher: Callable[..., Awaitable[list[dict[str, object]]]],
        factory: Callable[[FabricClient, dict[str, object]], T],
        fetcher_args: tuple[object, ...] = (),
        fetcher_kwargs: dict[str, object] | None = None,
    ) -> None:
        """Initialize the lazy collection."""
        self._client = client
        self._fetcher = fetcher
        self._factory = factory
        self._fetcher_args = fetcher_args
        self._fetcher_kwargs = fetcher_kwargs or {}
        self._items: list[T] | None = None
        self._logger = client._logger_factory.get_logger(__name__)

    async def _load(self) -> list[T]:
        """Fetch items from the API and cache them."""
        self._logger.info("Loading lazy collection (cache miss)")
        _start = time.monotonic()
        raw_items = await self._fetcher(*self._fetcher_args, **self._fetcher_kwargs)
        self._items = [self._factory(self._client, item) for item in raw_items]
        self._logger.info(
            "Loaded %d items in %dms",
            len(self._items),
            int((time.monotonic() - _start) * 1000),
        )
        return self._items

    async def all(self) -> list[T]:
        """Return all items as a list."""
        if self._items is None:
            await self._load()
        assert self._items is not None
        return list(self._items)

    async def first(self) -> T | None:
        """Return the first item, or None if the collection is empty."""
        items = await self.all()
        return items[0] if items else None

    async def __aiter__(self) -> AsyncIterator[T]:
        """Iterate asynchronously over all items."""
        items = await self.all()
        for item in items:
            yield item

    async def __len__(self) -> int:
        """Return the total number of items."""
        items = await self.all()
        return len(items)

    def __repr__(self) -> str:
        """Return a debug representation."""
        status = "loaded" if self._items is not None else "unloaded"
        count = len(self._items) if self._items is not None else "?"
        return f"<LazyCollection [{status}] count={count}>"


class _AsyncListProxy[T]:
    """Lightweight proxy that wraps an async fetcher with ``await`` / ``async for``.

    Used internally for lazy properties like ``dataset.refreshes``
    and ``dataflow.transactions``.
    """

    def __init__(
        self,
        fetcher: Callable[[], Coroutine[Any, Any, list[T]]],
    ) -> None:
        """Initialize with an async fetcher callable."""
        self._fetcher = fetcher
        self._cached: list[T] | None = None

    async def _resolve(self) -> list[T]:
        if self._cached is None:
            self._cached = await self._fetcher()
        return self._cached

    def __await__(self) -> Generator[Any, None, list[T]]:
        return self._resolve().__await__()

    async def __aiter__(self) -> AsyncIterator[T]:
        for item in await self._resolve():
            yield item
