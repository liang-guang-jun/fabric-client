"""Lazy-loaded paginated collection."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import TYPE_CHECKING, TypeVar

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

    async def _load(self) -> list[T]:
        """Fetch items from the API and cache them."""
        raw_items = await self._fetcher(
            *self._fetcher_args, **self._fetcher_kwargs
        )
        self._items = [self._factory(self._client, item) for item in raw_items]
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
