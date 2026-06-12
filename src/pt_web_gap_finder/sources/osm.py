from __future__ import annotations

import re
from typing import Any

import httpx

from pt_web_gap_finder.config import Settings
from pt_web_gap_finder.models import Address, CompanyLead, Confidence, Contacts, EvidenceItem, OnlinePresence
from pt_web_gap_finder.normalization.urls import normalize_url
from pt_web_gap_finder.sources.base import SourceQuery

CATEGORY_FILTERS: dict[str, list[tuple[str, str]]] = {
    "restaurant": [("amenity", "restaurant")],
    "cafe": [("amenity", "cafe")],
    "bar": [("amenity", "bar"), ("amenity", "pub")],
    "fast_food": [("amenity", "fast_food")],
    "dentist": [("amenity", "dentist"), ("healthcare", "dentist")],
    "pharmacy": [("amenity", "pharmacy"), ("healthcare", "pharmacy")],
    "clinic": [("amenity", "clinic"), ("healthcare", "clinic")],
    "hairdresser": [("shop", "hairdresser")],
    "real_estate": [("office", "estate_agent")],
    "gym": [("leisure", "fitness_centre")],
    "bakery": [("shop", "bakery")],
    "car_repair": [("shop", "car_repair")],
}

OSM_SOURCE_NAME = "OpenStreetMap"


class OSMOverpassAdapter:
    name = "osm"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()

    async def fetch_elements(self, query: SourceQuery) -> list[dict[str, Any]]:
        overpass_query = build_overpass_query(query)
        headers = {"User-Agent": self.settings.user_agent}
        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds, headers=headers) as client:
            response = await client.post(self.settings.overpass_url, data={"data": overpass_query})
            response.raise_for_status()
            payload = response.json()
        elements = payload.get("elements") or []
        return elements[: query.limit]


def build_overpass_query(query: SourceQuery) -> str:
    """Build an Overpass QL query for the MVP bbox flow."""
    if not query.bbox:
        raise ValueError("MVP Overpass query builder requires bbox")
    if not query.category or query.category not in CATEGORY_FILTERS:
        raise ValueError(f"Unsupported category: {query.category!r}")

    min_lon, min_lat, max_lon, max_lat = query.bbox
    bbox = f"{min_lat},{min_lon},{max_lat},{max_lon}"
    filters = CATEGORY_FILTERS[query.category]
    clauses = []
    for key, value in filters:
        clauses.extend(
            [
                f'node["{key}"="{value}"]({bbox});',
                f'way["{key}"="{value}"]({bbox});',
                f'relation["{key}"="{value}"]({bbox});',
            ]
        )
    body = "\n  ".join(clauses)
    return f"""[out:json][timeout:25];
(
  {body}
);
out center tags {query.limit};"""


def parse_osm_element(element: dict[str, Any], category: str | None = None) -> CompanyLead:
    tags = element.get("tags") or {}
    element_type = str(element["type"])
    element_id = str(element["id"])
    osm_id = f"osm:{element_type}:{element_id}"
    source_url = f"https://www.openstreetmap.org/{element_type}/{element_id}"

    name = tags.get("name") or tags.get("brand") or "Unnamed business"
    lat = element.get("lat") or (element.get("center") or {}).get("lat")
    lon = element.get("lon") or (element.get("center") or {}).get("lon")

    website = _first_tag(tags, ["website", "contact:website", "url"])
    normalized_website = normalize_url(website)
    social_profiles = _social_profiles(tags)

    evidence = [
        _evidence("name", name, source_url, Confidence.HIGH if tags.get("name") else Confidence.LOW),
    ]
    if website:
        evidence.append(_evidence("website", normalized_website, source_url, Confidence.HIGH))
    else:
        evidence.append(
            _evidence(
                "website",
                None,
                source_url,
                Confidence.MEDIUM,
                "No website/contact:website/url tag present in OSM record; this is not proof of absence.",
            )
        )

    address = Address(
        street=_street_from_tags(tags),
        postal_code=tags.get("addr:postcode"),
        locality=tags.get("addr:city") or tags.get("addr:place"),
        municipality=tags.get("addr:municipality"),
        district=tags.get("addr:district"),
        lat=lat,
        lon=lon,
        raw={k: v for k, v in tags.items() if k.startswith("addr:")},
    )
    contacts = Contacts(
        phone=_first_tag(tags, ["phone", "contact:phone"]),
        mobile=_first_tag(tags, ["mobile", "contact:mobile"]),
        email=_first_tag(tags, ["email", "contact:email"]),
        social_profiles=social_profiles,
    )
    online = OnlinePresence(
        website_found=bool(normalized_website),
        website_url=normalized_website,
        website_discovery_method="osm_tag" if normalized_website else "osm_missing_website_tag",
        domain_confidence=1.0 if normalized_website else 0.0,
        social_only=bool(social_profiles and not normalized_website),
    )
    return CompanyLead(
        id=osm_id,
        name=name,
        normalized_name=_normalize_name(name),
        country="PT",
        category=category,
        source_ids=[osm_id],
        address=address,
        contacts=contacts,
        online_presence=online,
        evidence=evidence,
    )


def _first_tag(tags: dict[str, Any], keys: list[str]) -> str | None:
    for key in keys:
        value = tags.get(key)
        if value:
            return str(value)
    return None


def _social_profiles(tags: dict[str, Any]) -> dict[str, str]:
    profiles: dict[str, str] = {}
    facebook = _first_tag(tags, ["facebook", "contact:facebook"])
    instagram = _first_tag(tags, ["instagram", "contact:instagram"])
    if facebook:
        profiles["facebook"] = normalize_url(facebook) or facebook
    if instagram:
        profiles["instagram"] = normalize_url(instagram) or instagram
    return profiles


def _street_from_tags(tags: dict[str, Any]) -> str | None:
    street = tags.get("addr:street")
    number = tags.get("addr:housenumber")
    if street and number:
        return f"{street} {number}"
    return street or None


def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip()).casefold()


def _evidence(
    field: str,
    value: Any,
    source_url: str,
    confidence: Confidence,
    notes: str | None = None,
) -> EvidenceItem:
    return EvidenceItem(
        field=field,
        value=value,
        source_name=OSM_SOURCE_NAME,
        source_type="open_data",
        source_url=source_url,
        confidence=confidence,
        notes=notes,
    )
