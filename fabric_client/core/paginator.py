"""Generic async paginator for Microsoft REST APIs."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from typing import Any, TypeVar

T = TypeVar("T")

logger = logging.getLogger(__name__)


class Paginator(AsyncIterator[T]):
    """Generic async paginator for Microsoft REST APIs.

    Handles continuation tokens, next-link URLs, and skip/top pagination.
    """

    def __init__(
        self,
        fetcher: Callable[..., Any],
        items_key: str = "value",
        continuation_key: str | None = "continuationToken",
        max_items: int | None = None,
        page_delay: float = 0.0,
        **params: Any,  # noqa: ANN401
    ) -> None:
        """Initialize the paginator."""
        self._fetcher = fetcher
        self._items_key = items_key
        self._continuation_key = continuation_key
        self._max_items = max_items
        self._page_delay = page_delay
        self._params = params

        self._current_page: list[T] = []
        self._page_index = 0
        self._fetched_count = 0
        self._continuation_token: str | None = None
        self._exhausted = False

    def __aiter__(self) -> AsyncIterator[T]:
        """Return self as the async iterator."""
        return self

    async def __anext__(self) -> T:
        """Return the next item from the current page."""
        if (
            self._max_items is not None
            and self._fetched_count >= self._max_items
        ):
            raise StopAsyncIteration

        if self._page_index >= len(self._current_page):
            if self._exhausted:
                raise StopAsyncIteration
            await self._fetch_next_page()

        item = self._current_page[self._page_index]
        self._page_index += 1
        self._fetched_count += 1
        return item

    async def _fetch_next_page(self) -> None:
        """Fetch the next page of results."""
        if (
            self._page_delay > 0
            and self._page_index == 0
            and self._current_page
        ):
            logger.debug(
                "Paginator: sleeping %.2fs before next page", self._page_delay
            )
            await asyncio.sleep(self._page_delay)

        params = {**self._params}
        if self._continuation_token:
            params["continuationToken"] = self._continuation_token

        response = await self._fetcher(**params)
        self._current_page = response.get(self._items_key, [])

        self._continuation_token = None
        if self._continuation_key:
            self._continuation_token = response.get(self._continuation_key)

        self._page_index = 0
        if not self._current_page:
            self._exhausted = True

    async def collect_all(self) -> list[T]:
        """Fetch all pages and return a single list."""
        result: list[T] = []
        async for item in self:
            result.append(item)
        return result
