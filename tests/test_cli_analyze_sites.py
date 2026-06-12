import json

from typer.testing import CliRunner

import pt_web_gap_finder.cli as cli_module
from pt_web_gap_finder.cli import app
from pt_web_gap_finder.models import CompanyLead, OnlinePresence, WebsiteAnalysis


def test_analyze_sites_reads_json_and_writes_enriched_json_csv_and_evidence(tmp_path, monkeypatch):
    input_path = tmp_path / "leads.json"
    json_output = tmp_path / "analyzed.json"
    csv_output = tmp_path / "analyzed.csv"
    evidence_output = tmp_path / "evidence.jsonl"
    lead = CompanyLead(
        id="osm:node:1",
        name="Empresa Exemplo",
        online_presence=OnlinePresence(website_found=True, website_url="https://empresa.example"),
    )
    input_path.write_text(json.dumps([lead.model_dump(mode="json")]), encoding="utf-8")

    def fake_run_site_analysis(leads, timeout, concurrency):
        assert timeout == 1.5
        assert concurrency == 2
        assert leads[0].name == "Empresa Exemplo"
        leads[0].website_analysis = WebsiteAnalysis(
            reachable=True,
            http_status=200,
            final_url="https://empresa.example/",
            https=True,
            title="Empresa Exemplo",
            meta_description_present=False,
            mobile_viewport_present=True,
            contact_signals=["email"],
        )
        leads[0].scores.opportunity_score = 5
        leads[0].scores.priority = "ignore"
        return leads

    monkeypatch.setattr(cli_module, "run_site_analysis_sync", fake_run_site_analysis)

    result = CliRunner().invoke(
        app,
        [
            "analyze-sites",
            "--input",
            str(input_path),
            "--output",
            str(json_output),
            "--csv-output",
            str(csv_output),
            "--evidence-output",
            str(evidence_output),
            "--timeout",
            "1.5",
            "--concurrency",
            "2",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Analyzed 1 leads" in result.output
    data = json.loads(json_output.read_text(encoding="utf-8"))
    assert data[0]["website_analysis"]["title"] == "Empresa Exemplo"
    assert "website_reachable" in csv_output.read_text(encoding="utf-8")
    assert evidence_output.exists()
