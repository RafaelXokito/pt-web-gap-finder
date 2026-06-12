import json

from typer.testing import CliRunner

import pt_web_gap_finder.cli as cli_module
from pt_web_gap_finder.cli import app
from pt_web_gap_finder.models import CompanyLead, OnlinePresence, WebsiteAnalysis


def test_run_command_scans_analyzes_and_writes_all_outputs(tmp_path, monkeypatch):
    scanned = CompanyLead(
        id="osm:node:1",
        name="Empresa Pipeline",
        category="restaurant",
        online_presence=OnlinePresence(website_found=True, website_url="https://pipeline.example"),
    )

    def fake_run_scan(query):
        assert query.bbox == (-8.75, 41.05, -8.45, 41.25)
        assert query.category == "restaurant"
        assert query.limit == 3
        return [scanned]

    def fake_run_site_analysis(leads, timeout, concurrency):
        assert timeout == 1.0
        assert concurrency == 2
        assert leads[0].name == "Empresa Pipeline"
        leads[0].website_analysis = WebsiteAnalysis(
            reachable=True,
            http_status=200,
            final_url="https://pipeline.example/",
            https=True,
            title="Empresa Pipeline",
            meta_description_present=False,
            mobile_viewport_present=True,
            contact_signals=["email"],
        )
        leads[0].scores.opportunity_score = 5
        leads[0].scores.priority = "ignore"
        return leads

    monkeypatch.setattr(cli_module, "run_scan", fake_run_scan)
    monkeypatch.setattr(cli_module, "run_site_analysis_sync", fake_run_site_analysis)

    output_dir = tmp_path / "run-output"
    result = CliRunner().invoke(
        app,
        [
            "run",
            "--bbox",
            "-8.75,41.05,-8.45,41.25",
            "--category",
            "restaurant",
            "--limit",
            "3",
            "--output-dir",
            str(output_dir),
            "--timeout",
            "1.0",
            "--concurrency",
            "2",
            "--top",
            "1",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Completed pipeline" in result.output
    expected = {
        "leads.csv",
        "leads.json",
        "evidence.jsonl",
        "analyzed.csv",
        "analyzed.json",
        "analyzed-evidence.jsonl",
        "report.md",
    }
    assert expected == {path.name for path in output_dir.iterdir()}
    analyzed = json.loads((output_dir / "analyzed.json").read_text(encoding="utf-8"))
    assert analyzed[0]["website_analysis"]["title"] == "Empresa Pipeline"
    assert "Empresa Pipeline" in (output_dir / "report.md").read_text(encoding="utf-8")


def test_run_command_rejects_unsupported_format(tmp_path):
    result = CliRunner().invoke(
        app,
        [
            "run",
            "--bbox",
            "-8.75,41.05,-8.45,41.25",
            "--category",
            "restaurant",
            "--output-dir",
            str(tmp_path),
            "--format",
            "html",
        ],
    )

    assert result.exit_code != 0
    assert "markdown format only" in result.output
