import csv
import json

from pt_web_gap_finder.models import CompanyLead, EvidenceItem, OnlinePresence
from pt_web_gap_finder.output.csv_export import write_leads_csv
from pt_web_gap_finder.output.json_export import write_leads_json, write_evidence_jsonl


def sample_lead() -> CompanyLead:
    return CompanyLead(
        id="osm:node:1",
        name="Café Exemplo",
        category="cafe",
        online_presence=OnlinePresence(website_found=False),
        evidence=[
            EvidenceItem(
                field="name",
                value="Café Exemplo",
                source_name="OpenStreetMap",
                source_type="open_data",
                source_url="https://www.openstreetmap.org/node/1",
            )
        ],
    )


def test_write_leads_csv_flattens_core_fields(tmp_path):
    output = tmp_path / "leads.csv"
    lead = sample_lead()
    lead.scores.opportunity_score = 45
    lead.scores.priority = "warm"

    write_leads_csv([lead], output)

    rows = list(csv.DictReader(output.open(newline="", encoding="utf-8")))
    assert rows == [
        {
            "id": "osm:node:1",
            "name": "Café Exemplo",
            "category": "cafe",
            "municipality": "",
            "district": "",
            "phone": "",
            "email": "",
            "website_found": "False",
            "website_url": "",
            "opportunity_score": "45",
            "confidence_score": "0",
            "priority": "warm",
            "reasons": "",
            "evidence_count": "1",
        }
    ]


def test_write_leads_json_preserves_nested_evidence(tmp_path):
    output = tmp_path / "leads.json"

    write_leads_json([sample_lead()], output)

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data[0]["name"] == "Café Exemplo"
    assert data[0]["evidence"][0]["source_name"] == "OpenStreetMap"


def test_write_evidence_jsonl_writes_one_evidence_item_per_line(tmp_path):
    output = tmp_path / "evidence.jsonl"

    write_evidence_jsonl([sample_lead()], output)

    lines = output.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    item = json.loads(lines[0])
    assert item["lead_id"] == "osm:node:1"
    assert item["field"] == "name"
