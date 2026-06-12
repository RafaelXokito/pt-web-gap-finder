from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, Protocol

import httpx

from pt_web_gap_finder.models import CompanyLead, EvidenceItem, WebsiteAnalysis
from pt_web_gap_finder.normalization.urls import normalize_url
from pt_web_gap_finder.scoring.lead_score import score_lead


@dataclass(frozen=True)
class SiteFetchResult:
    status_code: int
    url: str
    history: list[str]
    text: str


class SiteHTTPClient(Protocol):
    async def fetch(self, url: str, timeout: float) -> SiteFetchResult: ...


class HTTPXSiteClient:
    async def fetch(self, url: str, timeout: float) -> SiteFetchResult:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            response = await client.get(url, headers={"User-Agent": "pt-web-gap-finder/0.1"})
        return SiteFetchResult(
            status_code=response.status_code,
            url=str(response.url),
            history=[str(item.url) for item in response.history],
            text=response.text,
        )


class StaticHTTPClient:
    """Deterministic in-memory HTTP client for tests and local dry runs."""

    def __init__(self, responses: dict[str, dict[str, Any] | BaseException]) -> None:
        self.responses = responses

    async def fetch(self, url: str, timeout: float) -> SiteFetchResult:
        del timeout
        response = self.responses[url]
        if isinstance(response, BaseException):
            raise response
        return SiteFetchResult(
            status_code=int(response["status_code"]),
            url=str(response["url"]),
            history=list(response.get("history", [])),
            text=str(response.get("text", "")),
        )


class HomepageSignalParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title_parts: list[str] = []
        self._in_title = False
        self.meta_description_present = False
        self.mobile_viewport_present = False
        self.contact_signals: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key.lower(): (value or "") for key, value in attrs}
        tag = tag.lower()
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            name = attr.get("name", "").lower()
            if name == "description" and attr.get("content", "").strip():
                self.meta_description_present = True
            if name == "viewport" and attr.get("content", "").strip():
                self.mobile_viewport_present = True
        if tag == "a":
            href = attr.get("href", "").strip().lower()
            label = attr.get("aria-label", "").lower()
            combined = f"{href} {label}"
            if href.startswith("mailto:"):
                self.contact_signals.add("email")
            if href.startswith("tel:"):
                self.contact_signals.add("phone")
            if any(token in combined for token in ("contact", "contacto", "contactos")):
                self.contact_signals.add("contact_page")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
        lowered = data.lower()
        if re.search(r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b", lowered):
            self.contact_signals.add("email")
        if any(token in lowered for token in ("telefone", "telemóvel", "tlm", "contactos")):
            self.contact_signals.add("phone")

    @property
    def title(self) -> str | None:
        value = " ".join(part.strip() for part in self.title_parts if part.strip())
        return value or None


def extract_homepage_signals(html: str) -> tuple[str | None, bool, bool, list[str]]:
    parser = HomepageSignalParser()
    parser.feed(html)
    return (
        parser.title,
        parser.meta_description_present,
        parser.mobile_viewport_present,
        sorted(parser.contact_signals, key=("contact_page", "email", "phone").index),
    )


async def analyze_lead_site(
    lead: CompanyLead,
    *,
    client: SiteHTTPClient | None = None,
    timeout: float = 10.0,
) -> CompanyLead:
    url = normalize_url(lead.online_presence.website_url)
    if not url:
        lead.scores = score_lead(lead)
        return lead

    client = client or HTTPXSiteClient()
    try:
        fetched = await client.fetch(url, timeout=timeout)
    except Exception as exc:  # noqa: BLE001 - preserve network failure as evidence, not crash batch
        lead.website_analysis = WebsiteAnalysis(
            reachable=False,
            final_url=url,
            https=url.startswith("https://"),
            notes=[str(exc) or exc.__class__.__name__],
        )
        lead.evidence.append(
            EvidenceItem(
                field="website_analysis.reachable",
                value=False,
                source_name="Homepage HTTP check",
                source_type="derived",
                source_url=url,
                notes=str(exc) or exc.__class__.__name__,
            )
        )
        lead.scores = score_lead(lead)
        return lead

    title, has_meta, has_viewport, contact_signals = extract_homepage_signals(fetched.text)
    reachable = 200 <= fetched.status_code < 400
    lead.website_analysis = WebsiteAnalysis(
        http_status=fetched.status_code,
        final_url=fetched.url,
        https=fetched.url.startswith("https://"),
        reachable=reachable,
        redirect_chain=fetched.history,
        title=title,
        meta_description_present=has_meta,
        mobile_viewport_present=has_viewport,
        contact_signals=contact_signals,
    )
    lead.evidence.extend(
        [
            EvidenceItem(
                field="website_analysis.reachable",
                value=reachable,
                source_name="Homepage HTTP check",
                source_type="company_website",
                source_url=fetched.url,
            ),
            EvidenceItem(
                field="website_analysis.title",
                value=title,
                source_name="Homepage HTML",
                source_type="company_website",
                source_url=fetched.url,
            ),
        ]
    )
    lead.scores = score_lead(lead)
    return lead


async def run_site_analysis(
    leads: list[CompanyLead],
    *,
    client: SiteHTTPClient | None = None,
    timeout: float = 10.0,
    concurrency: int = 5,
) -> list[CompanyLead]:
    semaphore = asyncio.Semaphore(concurrency)

    async def analyze_one(lead: CompanyLead) -> CompanyLead:
        async with semaphore:
            return await analyze_lead_site(lead, client=client, timeout=timeout)

    return await asyncio.gather(*(analyze_one(lead) for lead in leads))


def run_site_analysis_sync(
    leads: list[CompanyLead], timeout: float = 10.0, concurrency: int = 5
) -> list[CompanyLead]:
    return asyncio.run(run_site_analysis(leads, timeout=timeout, concurrency=concurrency))
