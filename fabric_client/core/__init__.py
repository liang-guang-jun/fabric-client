"""Core abstractions: Resource, HTTP, pagination, caching."""

from __future__ import annotations

from fabric_client.core.cache import Cache
from fabric_client.core.collection import LazyCollection
from fabric_client.core.endpoint import Endpoint
from fabric_client.core.http import AsyncHttpClient, HttpResponse
from fabric_client.core.paginator import Paginator
from fabric_client.core.resource import Resource

__all__ = [
    "AsyncHttpClient",
    "Cache",
    "Endpoint",
    "HttpResponse",
    "LazyCollection",
    "Paginator",
    "Resource",
]
