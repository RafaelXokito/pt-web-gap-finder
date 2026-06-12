# Python CLI Plan

## 1. Technology choices

- Packaging: `pyproject.toml` with `hatchling`.
- CLI: `typer` for subcommands and nice help output.
- Models: `pydantic` for normalized records and validation.
- HTTP: `httpx` with async client and timeouts.
- Output: stdlib `csv`, `json`, and Markdown templates.
- UX: `rich` for progress and summaries.
- Tests: `pytest`.

## 2. Command surface

### `scan`

Discover businesses and optionally perform lightweight enrichment.

```bash
pt-web-gap-finder scan   --country PT   --municipality Porto   --category restaurant   --source osm   --limit 100   --output outputs/porto-restaurants.csv   --json-output outputs/porto-restaurants.json   --evidence-output outputs/porto-restaurants-evidence.jsonl
```

Options:

- `--country PT`
- `--district TEXT`
- `--municipality TEXT`
- `--bbox min_lon,min_lat,max_lon,max_lat`
- `--category TEXT`
- `--source osm` repeatable later
- `--limit INTEGER`
- `--include-website-check / --no-include-website-check`
- `--output PATH`
- `--json-output PATH`
- `--evidence-output PATH`
- `--rate-limit FLOAT`

### `analyze-sites`

Analyze known/found websites from a previous lead file.

```bash
pt-web-gap-finder analyze-sites   --input outputs/porto-restaurants.csv   --output outputs/porto-restaurants-analyzed.csv   --timeout 10   --concurrency 5
```

MVP checks:

- HTTP reachability;
- HTTPS;
- redirects;
- title/meta/viewport;
- contact signals;
- parked/under-construction signals.

### `score`

Recompute lead scores after enrichment.

```bash
pt-web-gap-finder score   --input outputs/porto-restaurants-analyzed.csv   --output outputs/porto-restaurants-scored.csv
```

### `report`

Generate Markdown report from a lead file.

```bash
pt-web-gap-finder report   --input outputs/porto-restaurants-scored.csv   --format markdown   --top 50   --output outputs/porto-restaurants-report.md
```

Report sections:

- scan parameters;
- source attribution;
- total leads;
- hot/warm/low counts;
- top opportunities;
- evidence caveats;
- recommended outreach segments.

### `sources list`

List available source adapters and their status.

```bash
pt-web-gap-finder sources list
```

### `sources inspect`

Show source license, terms notes, fields, and supported filters.

```bash
pt-web-gap-finder sources inspect osm
```

## 3. Folder structure

```text
src/pt_web_gap_finder/
  __init__.py
  cli.py                    # Typer app and command registration
  config.py                 # Runtime settings, env loading later
  models.py                 # Pydantic canonical models
  logging.py                # Rich/logging helpers later

  sources/
    __init__.py
    base.py                 # SourceAdapter protocol and SourceQuery
    osm.py                  # Overpass adapter
    registry.py             # adapter lookup

  normalization/
    __init__.py
    names.py
    urls.py
    phones.py

  enrichment/
    __init__.py
    website_discovery.py    # search API/domain candidate logic later
    website_analysis.py     # HTTP/HTML checks

  scoring/
    __init__.py
    lead_score.py           # opportunity scoring and reason generation

  output/
    __init__.py
    csv_export.py
    json_export.py
    markdown_report.py
```

## 4. Implementation phases

### Phase 1 — project skeleton

- Create package and CLI entrypoint.
- Add `--help` smoke test.
- Add canonical Pydantic models.
- Add scoring stub.

### Phase 2 — OSM adapter

- Implement Overpass query builder for categories and bbox/municipality.
- Start with bbox support because it avoids geocoding dependency.
- Add category mapping table.
- Parse OSM nodes/ways/relations into raw records.
- Add OSM attribution in outputs.

### Phase 3 — output exporters

- CSV export for spreadsheet workflows.
- JSON export preserving nested evidence.
- JSONL evidence ledger.
- Markdown report.

### Phase 4 — website analysis MVP

- Normalize URLs.
- Fetch homepage with timeout and safe redirect limit.
- Parse basic HTML signals.
- Return `WebsiteAnalysis` evidence items.

### Phase 5 — scoring

- Implement scoring rules from `docs/technical-specification.md`.
- Store score, priority, and human-readable reasons.

### Phase 6 — website discovery

- Add optional search API provider abstraction.
- Implement Brave/Bing as first adapters only if API keys are configured.
- Domain guessing remains low-confidence and clearly labeled.

### Phase 7 — official source adapters

Add one sector source at a time after manual source/terms review.

Recommended order:

1. tourism/accommodation;
2. health providers;
3. construction/real-estate;
4. public procurement suppliers.

## 5. Testing plan

Tests should avoid live network by default.

- `tests/test_models.py`
- `tests/test_scoring.py`
- `tests/test_url_normalization.py`
- `tests/test_osm_query.py`
- `tests/test_csv_export.py`
- `tests/test_cli_help.py`

Live integration tests can be gated behind env vars:

```bash
PT_WEB_GAP_FINDER_LIVE=1 pytest tests/integration -q
```

## 6. First executable milestone

A useful first milestone is:

```bash
pt-web-gap-finder scan --bbox -8.75,41.05,-8.45,41.25 --category restaurant --limit 25 --output outputs/sample.csv
```

Expected result:

- 25 or fewer OSM-derived records;
- website/source website field captured if present;
- missing website flag if absent;
- evidence for every OSM-derived field;
- CSV opens cleanly in spreadsheet software.
