"""Base Resource class with optional Pydantic validation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar, cast

import pydantic

if TYPE_CHECKING:
    from fabric_client.client import FabricClient

T = TypeVar("T", bound="Resource[Any]")


class Resource[M: pydantic.BaseModel]:
    """Base class for all Fabric / Power BI resources.

    Subclasses may optionally declare a Pydantic model via the ``_model``
    class attribute to enable validated access through :attr:`pydantic`::

        class WorkspaceModel(pydantic.BaseModel):
            id: str
            displayName: str

        class Workspace(Resource[WorkspaceModel]):
            _model = WorkspaceModel

        ws = await client.workspaces.get(...)
        print(ws.pydantic.displayName)  # fully typed & validated

    Resources *without* a model work as before — access raw data through
    the convenience properties.
    """

    # API path component for this resource type (e.g. "workspaces", "datasets")
    _api_path: str = ""

    # Pydantic model for validated access (set by subclasses)
    _model: type[M] | None = None

    def __init__(self, client: FabricClient, data: dict[str, Any]) -> None:
        """Initialize a resource instance."""
        self._client = client
        self._data = data
        self._pydantic: M | None = None

    def __repr__(self) -> str:
        """Return a human-readable representation."""
        name = (
            self._data.get("displayName")
            or self._data.get("name")
            or self._data.get("id", "?")
        )
        return f"<{type(self).__name__} {name!r}>"

    @property
    def id(self) -> str:
        """The unique identifier of this resource."""
        return cast(str, self._data.get("id") or self._data.get("objectId"))

    @property
    def raw(self) -> dict[str, Any]:
        """Raw JSON data from the API response."""
        return dict(self._data)

    @property
    def pydantic(self) -> M:
        """Validated Pydantic model instance built from the raw API response.

        Cached on first access — subsequent reads return the same instance.

        Raises:
            NotImplementedError: If the subclass did not set ``_model``.
        """
        if self._pydantic is not None:
            return self._pydantic
        if self._model is None:
            raise NotImplementedError(
                f"{type(self).__name__} does not declare a _model; "
                f"set _model = YourPydanticModel on the class."
            )
        self._pydantic = self._model.model_validate(self._data)
        return self._pydantic

    @property
    def extra(self) -> dict[str, Any]:
        """API fields in the raw response not covered by the Pydantic model.

        Useful during development to discover unmapped fields.

        Returns an empty dict when coverage is complete.
        """
        if self._model is None:
            return dict(self._data)
        known: set[str] = set()
        for name, field_info in self._model.model_fields.items():
            known.add(name)
            if field_info.alias:
                known.add(field_info.alias)
            va = field_info.validation_alias
            if va is not None:
                if isinstance(va, str):
                    known.add(va)
                else:
                    # AliasChoices — collect all alternative names
                    for choice in va.choices:  # type: ignore[union-attr]
                        if isinstance(choice, str):
                            known.add(choice)
        return {k: v for k, v in self._data.items() if k not in known}

    def to_dict(self) -> dict[str, Any]:
        """Serialize this resource to a dictionary."""
        return self.raw

    async def refresh(self) -> None:
        """Refresh this resource's data from the API."""
        raise NotImplementedError

    @classmethod
    def _from_data(cls: type[T], client: FabricClient, data: dict[str, Any]) -> T:
        """Create a resource instance from raw API data."""
        return cls(client, data)
