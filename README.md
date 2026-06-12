# PT Web Gap Finder

Portugal-focused company prospecting and website-gap analysis CLI.

The project finds Portuguese businesses from public/open/official sources, enriches them with evidence-backed contact and online-presence data, checks whether they have no website or a weak website, and exports prioritized lead lists for website creation/redesign outreach.

## Current status

Early design + skeleton. The first MVP targets:

- Source: OpenStreetMap Overpass API
- Region filter: Portugal municipality/district/bounding box
- Category filter: local business verticals
- Enrichment: website discovery and basic website health checks
- Output: CSV, JSON, Markdown report, evidence ledger

## Repository layout

```text
pt-web-gap-finder/
  docs/
    technical-specification.md
    python-cli-plan.md
    data-sources.md
  src/pt_web_gap_finder/
    cli.py
    config.py
    models.py
    sources/
    enrichment/
    scoring/
    output/
  tests/
```

## Planned CLI

```bash
pt-web-gap-finder scan --country PT --municipality Porto --category restaurant --limit 100 --output leads.csv
pt-web-gap-finder analyze-sites --input leads.csv --output enriched.csv
pt-web-gap-finder report --input enriched.csv --format markdown --output report.md
```

## Legal and ethical default

This project is intended to use public/open/official sources and allowed APIs. It should not scrape restricted platforms, collect private personal contacts, or claim certainty where the evidence is incomplete.
