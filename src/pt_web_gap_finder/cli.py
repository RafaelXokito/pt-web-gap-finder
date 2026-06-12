from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from pt_web_gap_finder import __version__
from pt_web_gap_finder.output.csv_export import write_leads_csv
from pt_web_gap_finder.output.json_export import write_evidence_jsonl, write_leads_json
from pt_web_gap_finder.pipeline import run_scan
from pt_web_gap_finder.sources.base import SourceQuery

app = typer.Typer(
    help="Portugal company prospecting and website-gap finder CLI.",
    invoke_without_command=True,
)
sources_app = typer.Typer(help="Inspect source adapters.")
app.add_typer(sources_app, name="sources")
console = Console()


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", help="Show version and exit."),
) -> None:
    if version:
        console.print(f"pt-web-gap-finder {__version__}")
        raise typer.Exit()


@app.command()
def scan(
    category: str = typer.Option(..., help="Business category, e.g. restaurant, dentist."),
    country: str = typer.Option("PT", help="Country code. MVP supports PT."),
    municipality: Optional[str] = typer.Option(None, help="Portuguese municipality/concelho."),
    district: Optional[str] = typer.Option(None, help="Portuguese district."),
    bbox: Optional[str] = typer.Option(None, help="min_lon,min_lat,max_lon,max_lat."),
    source: str = typer.Option("osm", help="Source adapter. MVP: osm."),
    limit: int = typer.Option(100, min=1, help="Maximum records."),
    output: Path = typer.Option(Path("outputs/leads.csv"), help="CSV output path."),
    json_output: Optional[Path] = typer.Option(None, help="JSON output path."),
    evidence_output: Optional[Path] = typer.Option(None, help="Evidence JSONL output path."),
) -> None:
    """Discover businesses and export a lead list."""
    if country != "PT":
        raise typer.BadParameter("MVP currently supports country PT only")
    if source != "osm":
        raise typer.BadParameter("MVP currently supports source osm only")

    parsed_bbox = _parse_bbox(bbox)
    query = SourceQuery(
        country=country,
        category=category,
        municipality=municipality,
        district=district,
        bbox=parsed_bbox,
        limit=limit,
    )
    leads = run_scan(query)
    write_leads_csv(leads, output)
    if json_output:
        write_leads_json(leads, json_output)
    if evidence_output:
        write_evidence_jsonl(leads, evidence_output)
    console.print(f"[green]Wrote {len(leads)} leads[/green] to {output}")


def _parse_bbox(value: str | None) -> tuple[float, float, float, float]:
    if not value:
        raise typer.BadParameter("bbox must be provided as min_lon,min_lat,max_lon,max_lat")
    try:
        parts = tuple(float(part.strip()) for part in value.split(","))
    except ValueError as exc:
        raise typer.BadParameter("bbox must be four comma-separated numbers") from exc
    if len(parts) != 4:
        raise typer.BadParameter("bbox must be four comma-separated numbers")
    min_lon, min_lat, max_lon, max_lat = parts
    if min_lon >= max_lon or min_lat >= max_lat:
        raise typer.BadParameter("bbox min values must be smaller than max values")
    return min_lon, min_lat, max_lon, max_lat


@app.command("analyze-sites")
def analyze_sites(
    input: Path = typer.Option(..., "--input", help="Input CSV/JSON lead file."),
    output: Path = typer.Option(..., help="Output enriched lead file."),
    timeout: float = typer.Option(10.0, help="HTTP timeout seconds."),
    concurrency: int = typer.Option(5, help="Maximum concurrent site checks."),
) -> None:
    """Analyze website reachability and basic quality signals."""
    console.print("[yellow]analyze-sites is not implemented yet.[/yellow]")
    console.print({"input": str(input), "output": str(output), "timeout": timeout, "concurrency": concurrency})
    raise typer.Exit(code=2)


@app.command()
def report(
    input: Path = typer.Option(..., "--input", help="Input scored lead file."),
    output: Path = typer.Option(Path("outputs/report.md"), help="Markdown report output."),
    top: int = typer.Option(50, min=1, help="Top lead count."),
    format: str = typer.Option("markdown", help="Report format. MVP: markdown."),
) -> None:
    """Generate a prospecting report."""
    console.print("[yellow]report is not implemented yet.[/yellow]")
    console.print({"input": str(input), "output": str(output), "top": top, "format": format})
    raise typer.Exit(code=2)


@sources_app.command("list")
def sources_list() -> None:
    """List source adapters."""
    console.print("osm	planned	OpenStreetMap Overpass API")


@sources_app.command("inspect")
def sources_inspect(name: str) -> None:
    """Inspect one source adapter."""
    if name != "osm":
        console.print(f"[red]Unknown source:[/red] {name}")
        raise typer.Exit(code=1)
    console.print("OpenStreetMap / Overpass API")
    console.print("Status: planned first adapter")
    console.print("License: ODbL; attribution required")
    console.print("Strength: open local-business discovery")
    console.print("Caveat: missing website tag is not proof of no website")
