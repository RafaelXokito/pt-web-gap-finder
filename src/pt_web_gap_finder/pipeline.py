from __future__ import annotations

import asyncio
from typing import Protocol

from pt_web_gap_finder.models import CompanyLead
from pt_web_gap_finder.scoring.lead_score import score_lead
from pt_web_gap_finder.sources.base import SourceQuery
from pt_web_gap_finder.sources.osm import OSMOverpassAdapter, parse_osm_element


class ElementAdapter(Protocol):
    async def fetch_elements(self, query: SourceQuery) -> list[dict]: ...


def run_scan(query: SourceQuery, adapter: ElementAdapter | None = None) -> list[CompanyLead]:
    """Run a source scan and return scored leads."""
    return asyncio.run(run_scan_async(query, adapter=adapter))


async def run_scan_async(query: SourceQuery, adapter: ElementAdapter | None = None) -> list[CompanyLead]:
    adapter = adapter or OSMOverpassAdapter()
    elements = await adapter.fetch_elements(query)
    leads: list[CompanyLead] = []
    for element in elements:
        tags = element.get("tags") or {}
        if not tags.get("name"):
            continue
        lead = parse_osm_element(element, category=query.category)
        lead.scores = score_lead(lead)
        leads.append(lead)
        if len(leads) >= query.limit:
            break
    return leads
