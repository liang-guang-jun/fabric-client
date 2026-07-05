"""Power Query extraction service for dataflows (Gen1 + Gen2)."""

from __future__ import annotations

import base64
import re
from collections.abc import AsyncIterator, Generator
from typing import Any

import pydantic

from fabric_client.models.dataflow import Dataflow


class PowerQuerySection(pydantic.BaseModel):
    """A single Power Query shared declaration from a dataflow or dataset."""

    name: str
    """The query / table name."""

    expression: str
    """The Power Query M expression body."""

    workspace_id: str | None = None
    """The workspace this source belongs to."""

    refreshable_type: str | None = None
    """The type of refreshable resource: ``dataflow`` or ``dataset``."""

    refreshable_id: str | None = None
    """The ID of the dataflow or dataset this source belongs to."""


class PowerQueryParser:
    """Extract Power Query ``shared`` expressions from a :class:`Dataflow`.

    Handles the two-generation split::

        Gen1 — Power BI admin export API  (GET /admin/dataflows/{id}/export)
        Gen2 — Fabric item definition API (POST /items/{id}/getDefinition)

    Usage::

        parser = PowerQueryParser(dataflow)
        sources = await parser.sources()
        async for s in parser:
            print(s.name, s.expression)
    """

    _SHARED_RE = re.compile(
        r"(?ms)^shared\s+((?:#\"(?:[^\"]|\"\")*\"|[A-Za-z_][\w]*))"
        r"\s*=\s*(.*?)(?=^\s*shared\s+|\Z)"
    )

    def __init__(self, dataflow: Dataflow) -> None:
        """Initialize with the target dataflow."""
        self._df = dataflow
        self._sources: list[PowerQuerySection] | None = None

    # -- public API ------------------------------------------------------------

    async def sources(self) -> list[PowerQuerySection]:
        """Fetch and parse sources (cached after first call)."""
        if self._sources is not None:
            return self._sources
        gen = self._df.pydantic.generation
        if gen == 1:
            pq = await self._fetch_gen1()
        elif gen == 2:
            pq = await self._fetch_gen2()
        else:
            self._sources = []
            return self._sources
        self._sources = self._parse(
            pq,
            workspace_id=self._df.pydantic.workspace_id,
            refreshable_type="dataflow",
            refreshable_id=self._df.id,
        )
        return self._sources

    def __await__(self) -> Generator[Any, None, list[PowerQuerySection]]:
        """Await and return the list of sources."""
        return self.sources().__await__()

    async def __aiter__(self) -> AsyncIterator[PowerQuerySection]:
        """Iterate asynchronously over sources."""
        for s in await self.sources():
            yield s

    # -- fetching --------------------------------------------------------------

    async def _fetch_gen1(self) -> str:
        """Gen1: admin export → extract mashup content."""
        from fabric_client.apis.powerbi.dataflows import DataflowsAPI

        api = DataflowsAPI(self._df._client)
        raw = await api.export_definition(self._df.id)

        # Try pbi_mashup.document (legacy shape)
        mashup = raw.get("pbi_mashup", {})
        if isinstance(mashup, dict):
            doc = mashup.get("document")
            if isinstance(doc, str):
                return doc

        # Try definition.parts with mashup.pq (Gen2-like shape)
        definition = raw.get("definition", {})
        if isinstance(definition, dict):
            parts = definition.get("parts", [])
            if isinstance(parts, list):
                for part in parts:
                    if isinstance(part, dict) and part.get("path") == "mashup.pq":
                        payload = part.get("payload", "")
                        if isinstance(payload, str):
                            return base64.b64decode(payload).decode(
                                "utf-8", errors="replace"
                            )

        # Fallback: deep-search for any Power Query content
        pq = self._search_pq(raw)
        if pq is not None:
            return pq

        raise ValueError(
            "Could not extract Power Query mashup from Gen1 dataflow export"
        )

    async def _fetch_gen2(self) -> str:
        """Gen2: get item definition → extract mashup.pq payload."""
        from fabric_client.apis.fabric.items import ItemsAPI

        ws_id = self._df.pydantic.workspace_id
        if not ws_id:
            raise ValueError(
                "Gen2 dataflow is missing workspace_id; cannot fetch definition"
            )
        api = ItemsAPI(self._df._client)
        definition = await api.get_definition(ws_id, self._df.id)
        def_body: dict[str, Any] = definition.get("definition", {})  # type: ignore[assignment]
        parts: list[dict[str, Any]] = def_body.get("parts", [])
        for part in parts:
            if part.get("path") == "mashup.pq":
                payload: str = part.get("payload", "")
                return base64.b64decode(payload).decode("utf-8", errors="replace")
        raise ValueError("No mashup.pq part found in Gen2 dataflow definition")

    # -- parsing ---------------------------------------------------------------

    @classmethod
    def _parse(
        cls,
        pq: str,
        *,
        workspace_id: str | None = None,
        refreshable_type: str | None = None,
        refreshable_id: str | None = None,
    ) -> list[PowerQuerySection]:
        """Parse ``shared`` expressions from a Power Query document."""
        sources: list[PowerQuerySection] = []
        for m in cls._SHARED_RE.finditer(pq):
            name = cls._unescape_name(m.group(1))
            expression = m.group(2).strip()
            sources.append(
                PowerQuerySection.model_validate(
                    {
                        "name": name,
                        "expression": expression,
                        "workspace_id": workspace_id,
                        "refreshable_type": refreshable_type,
                        "refreshable_id": refreshable_id,
                    }
                )
            )
        return sources

    @staticmethod
    def _unescape_name(raw: str) -> str:
        r"""Remove M quoting ``#"..."`` and double-quote escaping."""
        if raw.startswith('#"') and raw.endswith('"'):
            raw = raw[2:-1].replace('""', '"')
        return raw

    @staticmethod
    def _search_pq(obj: Any) -> str | None:  # noqa: ANN401
        """Deep-search an arbitrary JSON-like structure for Power Query content."""
        if isinstance(obj, str) and ("shared " in obj or "let " in obj):
            return obj
        if isinstance(obj, dict):
            for v in obj.values():
                found = PowerQueryParser._search_pq(v)
                if found:
                    return found
        if isinstance(obj, list):
            for item in obj:
                found = PowerQueryParser._search_pq(item)
                if found:
                    return found
        return None
