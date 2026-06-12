from pt_web_gap_finder.pipeline import run_scan
from pt_web_gap_finder.sources.base import SourceQuery


class FakeOSMAdapter:
    async def fetch_elements(self, query: SourceQuery):
        assert query.category == "restaurant"
        return [
            {
                "type": "node",
                "id": 1,
                "lat": 41.1,
                "lon": -8.6,
                "tags": {"name": "Restaurante Um", "amenity": "restaurant"},
            },
            {
                "type": "node",
                "id": 2,
                "lat": 41.2,
                "lon": -8.7,
                "tags": {"amenity": "restaurant"},
            },
        ]


def test_run_scan_uses_adapter_parses_named_leads_and_scores():
    query = SourceQuery(category="restaurant", bbox=(-8.75, 41.05, -8.45, 41.25), limit=10)

    leads = run_scan(query, adapter=FakeOSMAdapter())

    assert [lead.name for lead in leads] == ["Restaurante Um"]
    assert leads[0].scores.opportunity_score == 45
    assert leads[0].scores.priority in {"low", "warm", "hot"}
