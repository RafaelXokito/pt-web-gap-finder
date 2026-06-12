from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from pt_web_gap_finder import __version__
from pt_web_gap_finder.categories import CategoryNotFoundError, resolve_categories
from pt_web_gap_finder.models import CompanyLead, OnlinePresence
from pt_web_gap_finder.output.csv_export import write_leads_csv
from pt_web_gap_finder.output.json_export import write_evidence_jsonl, write_leads_json
from pt_web_gap_finder.pipeline import run_scan
from pt_web_gap_finder.places import PlaceNotFoundError, resolve_place
from pt_web_gap_finder.report import write_markdown_report
from pt_web_gap_finder.site_analysis import run_site_analysis_sync
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
    place: Optional[str] = typer.Option(None, help="Portugal place preset, e.g. porto, lisboa."),
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

    parsed_bbox, municipality, district = _resolve_location(
        bbox=bbox, place=place, municipality=municipality, district=district
    )
    leads = _run_scan_for_categories(
        category=category,
        country=country,
        municipality=municipality,
        district=district,
        bbox=parsed_bbox,
        limit=limit,
    )
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


def _resolve_location(
    *,
    bbox: str | None,
    place: str | None,
    municipality: str | None,
    district: str | None,
) -> tuple[tuple[float, float, float, float], str | None, str | None]:
    if bbox and place:
        raise typer.BadParameter("use either bbox or place, not both")
    if place:
        try:
            preset = resolve_place(place)
        except PlaceNotFoundError as exc:
            raise typer.BadParameter(str(exc)) from exc
        return preset.bbox, municipality or preset.municipality, district or preset.district
    return _parse_bbox(bbox), municipality, district


def _run_scan_for_categories(
    *,
    category: str,
    country: str,
    municipality: str | None,
    district: str | None,
    bbox: tuple[float, float, float, float],
    limit: int,
) -> list[CompanyLead]:
    try:
        categories = resolve_categories(category)
    except CategoryNotFoundError as exc:
        raise typer.BadParameter(str(exc)) from exc

    category_results: list[list[CompanyLead]] = []
    for resolved_category in categories:
        query = SourceQuery(
            country=country,
            category=resolved_category,
            municipality=municipality,
            district=district,
            bbox=bbox,
            limit=limit,
        )
        category_results.append(run_scan(query))

    leads_by_id: dict[str, CompanyLead] = {}
    max_result_count = max((len(results) for results in category_results), default=0)
    for index in range(max_result_count):
        for results in category_results:
            if index >= len(results):
                continue
            lead = results[index]
            leads_by_id.setdefault(lead.id, lead)
            if len(leads_by_id) >= limit:
                return list(leads_by_id.values())
    return list(leads_by_id.values())


@app.command()
def run(
    category: str = typer.Option(..., help="Business category, e.g. restaurant, dentist."),
    country: str = typer.Option("PT", help="Country code. MVP supports PT."),
    municipality: Optional[str] = typer.Option(None, help="Portuguese municipality/concelho."),
    district: Optional[str] = typer.Option(None, help="Portuguese district."),
    bbox: Optional[str] = typer.Option(None, help="min_lon,min_lat,max_lon,max_lat."),
    place: Optional[str] = typer.Option(None, help="Portugal place preset, e.g. porto, lisboa."),
    source: str = typer.Option("osm", help="Source adapter. MVP: osm."),
    limit: int = typer.Option(100, min=1, help="Maximum records."),
    output_dir: Path = typer.Option(Path("outputs/run"), help="Directory for all pipeline outputs."),
    timeout: float = typer.Option(10.0, help="HTTP timeout seconds for website analysis."),
    concurrency: int = typer.Option(5, min=1, help="Maximum concurrent site checks."),
    top: int = typer.Option(50, min=1, help="Top lead count for report."),
    format: str = typer.Option("markdown", help="Report format. MVP: markdown."),
) -> None:
    """Run scan, website analysis, and report generation in one command."""
    if country != "PT":
        raise typer.BadParameter("MVP currently supports country PT only")
    if source != "osm":
        raise typer.BadParameter("MVP currently supports source osm only")
    if format != "markdown":
        raise typer.BadParameter("MVP currently supports markdown format only")

    parsed_bbox, municipality, district = _resolve_location(
        bbox=bbox, place=place, municipality=municipality, district=district
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    leads = _run_scan_for_categories(
        category=category,
        country=country,
        municipality=municipality,
        district=district,
        bbox=parsed_bbox,
        limit=limit,
    )

    write_leads_csv(leads, output_dir / "leads.csv")
    write_leads_json(leads, output_dir / "leads.json")
    write_evidence_jsonl(leads, output_dir / "evidence.jsonl")

    analyzed = run_site_analysis_sync(leads, timeout=timeout, concurrency=concurrency)
    write_leads_csv(analyzed, output_dir / "analyzed.csv")
    write_leads_json(analyzed, output_dir / "analyzed.json")
    write_evidence_jsonl(analyzed, output_dir / "analyzed-evidence.jsonl")
    write_markdown_report(analyzed, output_dir / "report.md", top=top)

    console.print(f"[green]Completed pipeline[/green] for {len(analyzed)} leads in {output_dir}")


@app.command("analyze-sites")
def analyze_sites(
    input: Path = typer.Option(..., "--input", help="Input CSV/JSON lead file."),
    output: Path = typer.Option(..., help="Output enriched JSON lead file."),
    csv_output: Optional[Path] = typer.Option(None, help="Optional enriched CSV output path."),
    evidence_output: Optional[Path] = typer.Option(None, help="Optional evidence JSONL output path."),
    timeout: float = typer.Option(10.0, help="HTTP timeout seconds."),
    concurrency: int = typer.Option(5, min=1, help="Maximum concurrent site checks."),
) -> None:
    """Analyze website reachability and basic quality signals."""
    leads = _read_leads(input)
    analyzed = run_site_analysis_sync(leads, timeout=timeout, concurrency=concurrency)
    write_leads_json(analyzed, output)
    if csv_output:
        write_leads_csv(analyzed, csv_output)
    if evidence_output:
        write_evidence_jsonl(analyzed, evidence_output)
    console.print(f"[green]Analyzed {len(analyzed)} leads[/green] to {output}")


def _read_leads(input_path: Path) -> list[CompanyLead]:
    if input_path.suffix.lower() == ".json":
        data = json.loads(input_path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise typer.BadParameter("JSON input must contain a list of leads")
        return [CompanyLead.model_validate(item) for item in data]
    if input_path.suffix.lower() == ".csv":
        with input_path.open(newline="", encoding="utf-8") as handle:
            return [_lead_from_csv_row(row) for row in csv.DictReader(handle)]
    raise typer.BadParameter("input must be a .json or .csv lead export")


def _lead_from_csv_row(row: dict[str, str]) -> CompanyLead:
    website_url = row.get("website_url") or None
    website_found_raw = (row.get("website_found") or "").strip().lower()
    website_found = None
    if website_found_raw in {"true", "1", "yes"}:
        website_found = True
    elif website_found_raw in {"false", "0", "no"}:
        website_found = False
    return CompanyLead(
        id=row.get("id") or row.get("name") or "csv:unknown",
        name=row.get("name") or "",
        category=row.get("category") or None,
        online_presence=OnlinePresence(website_found=website_found, website_url=website_url),
    )


@app.command()
def report(
    input: Path = typer.Option(..., "--input", help="Input scored lead file."),
    output: Path = typer.Option(Path("outputs/report.md"), help="Markdown report output."),
    top: int = typer.Option(50, min=1, help="Top lead count."),
    format: str = typer.Option("markdown", help="Report format. MVP: markdown."),
) -> None:
    """Generate a prospecting report."""
    if format != "markdown":
        raise typer.BadParameter("MVP currently supports markdown format only")
    leads = _read_leads(input)
    write_markdown_report(leads, output, top=top)
    console.print(f"[green]Wrote report[/green] with {min(len(leads), top)} leads to {output}")


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
