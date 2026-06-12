from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from html import unescape
from typing import Protocol
from urllib.parse import urlparse

import httpx

from pt_web_gap_finder.models import CompanyLead, Confidence, EvidenceItem
from pt_web_gap_finder.normalization.urls import normalize_url
from pt_web_gap_finder.scoring.lead_score import score_lead

SOCIAL_HOST_MARKERS = (
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "tiktok.com",
    "x.com",
    "twitter.com",
    "youtube.com",
)
DIRECTORY_HOST_MARKERS = (
    "tripadvisor.",
    "thefork.",
    "ubereats.",
    "glovoapp.",
    "justeat.",
    "olx.",
    "idealista.",
    "imovirtual.",
    "yelp.",
    "mapcarta.",
    "yellowpages.",
    "guiaempresas.",
    "cybo.com",
    "starofservice.",
    "booksy.",
)
GENERIC_NAME_TOKENS = {
    "auto",
    "restaurante",
    "cafe",
    "café",
    "bar",
    "padaria",
    "barbearia",
    "clinica",
    "clínica",
    "centro",
    "loja",
    "oficina",
    "reparadora",
    "talho",
    "pastelaria",
    "farmacia",
    "farmácia",
    "gym",
}


@dataclass(frozen=True)
class SearchResult:
    url: str
    title: str
    snippet: str = ""


class SearchClient(Protocol):
    async def search(self, query: str, *, limit: int) -> list[SearchResult]: ...


class BingSearchClient:
    async def search(self, query: str, *, limit: int) -> list[SearchResult]:
        params = {"q": query, "setlang": "pt-PT"}
        headers = {"User-Agent": "Mozilla/5.0 pt-web-gap-finder/0.1"}
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=headers) as client:
            response = await client.get("https://www.bing.com/search", params=params)
            response.raise_for_status()
        return parse_bing_results(response.text, limit=limit)


class StaticSearchClient:
    def __init__(self, responses: dict[str, list[SearchResult]]) -> None:
        self.responses = responses

    async def search(self, query: str, *, limit: int) -> list[SearchResult]:
        return self.responses.get(query, [])[:limit]


def build_search_query(lead: CompanyLead) -> str:
    parts = [lead.name]
    if lead.address and lead.address.locality:
        parts.append(lead.address.locality)
    elif lead.address and lead.address.street:
        parts.append(lead.address.street)
    parts.append("Portugal")
    return " ".join(part.strip() for part in parts if part and part.strip())


async def verify_lead_website(
    lead: CompanyLead,
    *,
    client: SearchClient | None = None,
    limit: int = 5,
    provider: str = "bing",
) -> CompanyLead:
    if lead.online_presence.website_found:
        return lead

    client = client or _client_for_provider(provider)
    query = build_search_query(lead)
    results = await client.search(query, limit=limit)
    candidate_urls = [normalize_url(result.url) or result.url for result in results]
    lead.online_presence.search_candidates = candidate_urls

    official = _pick_official_website(results, lead)
    if official:
        lead.online_presence.website_found = True
        lead.online_presence.website_url = normalize_url(official.url)
        lead.online_presence.website_discovery_method = f"{provider}_search"
        lead.online_presence.domain_confidence = _estimate_domain_confidence(official, lead)
        lead.online_presence.social_only = False
        lead.evidence.append(
            EvidenceItem(
                field="online_presence.website_url",
                value=lead.online_presence.website_url,
                source_name="Bing Search" if provider == "bing" else provider,
                source_type="search_api",
                source_url=official.url,
                confidence=Confidence.MEDIUM,
                notes=f"Search verification candidate for query: {query}",
            )
        )
    else:
        lead.online_presence.website_found = False
        lead.online_presence.website_url = None
        lead.online_presence.domain_confidence = 0.0
        social_matches = [
            result
            for result in results
            if _is_social_url(normalize_url(result.url) or result.url) and _result_mentions_business(result, lead)
        ]
        if social_matches:
            lead.online_presence.social_only = True
            lead.online_presence.website_discovery_method = "search_social_only"
        else:
            lead.online_presence.social_only = False
            lead.online_presence.website_discovery_method = "search_no_website_found"
        lead.evidence.append(
            EvidenceItem(
                field="online_presence.search_candidates",
                value=candidate_urls,
                source_name="Bing Search" if provider == "bing" else provider,
                source_type="search_api",
                source_url=f"https://www.bing.com/search?q={query}" if provider == "bing" else None,
                confidence=Confidence.LOW,
                notes=f"Search verification found no clear official website for query: {query}",
            )
        )

    lead.scores = score_lead(lead)
    return lead


async def run_search_verification(
    leads: list[CompanyLead], *, provider: str = "bing", limit: int = 5, client: SearchClient | None = None
) -> list[CompanyLead]:
    resolved_client = client or _client_for_provider(provider)
    return await asyncio.gather(
        *(verify_lead_website(lead, client=resolved_client, limit=limit, provider=provider) for lead in leads)
    )


def run_search_verification_sync(
    leads: list[CompanyLead], *, provider: str = "bing", limit: int = 5, client: SearchClient | None = None
) -> list[CompanyLead]:
    return asyncio.run(run_search_verification(leads, provider=provider, limit=limit, client=client))


def _client_for_provider(provider: str) -> SearchClient:
    if provider != "bing":
        raise ValueError(f"unsupported search provider: {provider}")
    return BingSearchClient()


def parse_bing_results(html: str, *, limit: int) -> list[SearchResult]:
    results: list[SearchResult] = []
    for block in re.findall(r'<li class="b_algo".*?</li>', html, re.S):
        title_match = re.search(r'<h2[^>]*><a[^>]*>(.*?)</a></h2>', block, re.S)
        snippet_match = re.search(r'<p[^>]*>(.*?)</p>', block, re.S)
        cite_match = re.search(r'<cite>(.*?)</cite>', block, re.S)
        href_match = re.search(r'<a[^>]+href="(https?://[^"]+)"', block, re.S)
        if not title_match:
            continue
        raw_url = _strip_html(cite_match.group(1)) if cite_match else ""
        if not raw_url and href_match:
            raw_url = unescape(href_match.group(1))
        clean_url = normalize_url(raw_url)
        if not clean_url:
            continue
        clean_title = _strip_html(title_match.group(1))
        clean_snippet = _strip_html(snippet_match.group(1) if snippet_match else "")
        results.append(SearchResult(url=clean_url, title=clean_title, snippet=clean_snippet))
        if len(results) >= limit:
            break
    return results


def _pick_official_website(results: list[SearchResult], lead: CompanyLead) -> SearchResult | None:
    normalized_name = (lead.normalized_name or lead.name.casefold()).replace("&", " ")
    raw_tokens = [token for token in re.split(r"\W+", normalized_name) if len(token) >= 3]
    name_tokens = [token for token in raw_tokens if token not in GENERIC_NAME_TOKENS]
    for result in results:
        normalized_url = normalize_url(result.url)
        if not normalized_url:
            continue
        if _is_social_url(normalized_url) or _is_directory_url(normalized_url):
            continue
        host = (urlparse(normalized_url).hostname or "").casefold()
        title_text = f"{result.title} {result.snippet}".casefold()
        host_hits = sum(token in host for token in name_tokens[:4])
        title_hits = sum(token in title_text for token in name_tokens[:4])
        if host_hits >= 2:
            return result
        if host_hits >= 1 and title_hits >= 1:
            return result
        if not name_tokens and title_hits >= 2:
            return result
    return None


def _estimate_domain_confidence(result: SearchResult, lead: CompanyLead) -> float:
    normalized_url = normalize_url(result.url) or result.url
    host = (urlparse(normalized_url).hostname or "").casefold()
    normalized_name = (lead.normalized_name or lead.name.casefold()).replace("&", " ")
    raw_tokens = [token for token in re.split(r"\W+", normalized_name) if len(token) >= 3]
    tokens = [token for token in raw_tokens if token not in GENERIC_NAME_TOKENS]
    confidence = 0.55
    host_hits = sum(token in host for token in tokens[:4])
    if host_hits >= 2:
        confidence += 0.2
    elif host_hits == 1:
        confidence += 0.1
    title_text = f"{result.title} {result.snippet}".casefold()
    confidence += 0.05 * sum(token in title_text for token in tokens[:4])
    return min(confidence, 0.95)


def _result_mentions_business(result: SearchResult, lead: CompanyLead) -> bool:
    normalized_name = (lead.normalized_name or lead.name.casefold()).replace("&", " ")
    raw_tokens = [token for token in re.split(r"\W+", normalized_name) if len(token) >= 3]
    tokens = [token for token in raw_tokens if token not in GENERIC_NAME_TOKENS]
    haystack = f"{result.title} {result.snippet}".casefold()
    if not tokens:
        return False
    return sum(token in haystack for token in tokens[:4]) >= 1


def _is_social_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").casefold()
    return any(marker in host for marker in SOCIAL_HOST_MARKERS)


def _is_directory_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").casefold()
    return any(marker in host for marker in DIRECTORY_HOST_MARKERS)


def _strip_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", unescape(value or ""))
    return re.sub(r"\s+", " ", text).strip()
