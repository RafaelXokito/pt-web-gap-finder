import json

from typer.testing import CliRunner

from pt_web_gap_finder.cli import app
from pt_web_gap_finder.models import CompanyLead, LeadScores, OnlinePresence


def test_report_command_reads_json_and_writes_markdown(tmp_path):
    input_path = tmp_path / "analyzed.json"
    output_path = tmp_path / "report.md"
    lead = CompanyLead(
        id="osm:node:1",
        name="Empresa Sem Site",
        category="restaurant",
        online_presence=OnlinePresence(website_found=False),
        scores=LeadScores(
            opportunity_score=45,
            confidence_score=70,
            priority="low",
            reasons=["No website found in available evidence"],
        ),
    )
    input_path.write_text(json.dumps([lead.model_dump(mode="json")]), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "report",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--top",
            "1",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Wrote report" in result.output
    report = output_path.read_text(encoding="utf-8")
    assert "Empresa Sem Site" in report
    assert "Gap type: No website found" in report
