from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class SourceQuery:
    country: str = "PT"
    category: str | None = None
    municipality: str | None = None
    district: str | None = None
    bbox: tuple[float, float, float, float] | None = None
    limit: int = 100


@dataclass(frozen=True)
class RawBusinessRecord:
    source: str
    source_id: str
    raw: dict[str, Any]


class SourceAdapter(Protocol):
    name: str

    async def fetch(self, query: SourceQuery) -> list[RawBusinessRecord]:
        """Fetch raw business records for a query."""
        ...
