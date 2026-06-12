from pt_web_gap_finder.sources.base import SourceQuery
from pt_web_gap_finder.sources.osm import build_overpass_query


def test_build_overpass_query_for_restaurants_bbox():
    query = SourceQuery(category="restaurant", bbox=(-8.75, 41.05, -8.45, 41.25), limit=25)
    ql = build_overpass_query(query)
    assert '["amenity"="restaurant"]' in ql
    assert "41.05,-8.75,41.25,-8.45" in ql
    assert "out center tags 25" in ql
