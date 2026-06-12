from typer.testing import CliRunner

import pt_web_gap_finder.cli as cli_module
from pt_web_gap_finder.models import CompanyLead, OnlinePresence
from pt_web_gap_finder.cli import app


def test_scan_writes_csv_json_and_evidence_outputs(tmp_path, monkeypatch):
    lead = CompanyLead(
        id="osm:node:1",
        name="Restaurante Um",
        category="restaurant",
        online_presence=OnlinePresence(website_found=False),
    )
    lead.scores.opportunity_score = 45
    lead.scores.priority = "low"

    def fake_run_scan(query):
        assert query.bbox == (-8.75, 41.05, -8.45, 41.25)
        assert query.category == "restaurant"
        assert query.limit == 5
        return [lead]

    monkeypatch.setattr(cli_module, "run_scan", fake_run_scan)
    csv_path = tmp_path / "leads.csv"
    json_path = tmp_path / "leads.json"
    evidence_path = tmp_path / "evidence.jsonl"

    result = CliRunner().invoke(
        app,
        [
            "scan",
            "--bbox",
            "-8.75,41.05,-8.45,41.25",
            "--category",
            "restaurant",
            "--limit",
            "5",
            "--output",
            str(csv_path),
            "--json-output",
            str(json_path),
            "--evidence-output",
            str(evidence_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Wrote 1 leads" in result.output
    assert csv_path.exists()
    assert json_path.exists()
    assert evidence_path.exists()


def test_scan_accepts_place_preset_instead_of_manual_bbox(tmp_path, monkeypatch):
    lead = CompanyLead(
        id="osm:node:1",
        name="Restaurante Porto",
        category="restaurant",
        online_presence=OnlinePresence(website_found=False),
    )

    def fake_run_scan(query):
        assert query.bbox == (-8.69, 41.12, -8.55, 41.19)
        assert query.municipality == "Porto"
        return [lead]

    monkeypatch.setattr(cli_module, "run_scan", fake_run_scan)
    csv_path = tmp_path / "leads.csv"

    result = CliRunner().invoke(
        app,
        [
            "scan",
            "--place",
            "porto",
            "--category",
            "restaurant",
            "--output",
            str(csv_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert csv_path.exists()


def test_scan_rejects_malformed_bbox():
    result = CliRunner().invoke(
        app,
        ["scan", "--bbox", "bad", "--category", "restaurant"],
    )

    assert result.exit_code != 0
    assert "bbox must be" in result.output
