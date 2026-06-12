from typer.testing import CliRunner

from pt_web_gap_finder.cli import app


def test_cli_help_smoke():
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Portugal company prospecting" in result.output


def test_sources_list_smoke():
    result = CliRunner().invoke(app, ["sources", "list"])
    assert result.exit_code == 0
    assert "osm" in result.output
