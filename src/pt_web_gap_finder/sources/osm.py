from __future__ import annotations

from pt_web_gap_finder.sources.base import SourceQuery

CATEGORY_FILTERS: dict[str, list[tuple[str, str]]] = {
    "restaurant": [("amenity", "restaurant")],
    "cafe": [("amenity", "cafe")],
    "dentist": [("amenity", "dentist"), ("healthcare", "dentist")],
    "hairdresser": [("shop", "hairdresser")],
    "real_estate": [("office", "estate_agent")],
    "gym": [("leisure", "fitness_centre")],
}


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
