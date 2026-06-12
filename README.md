# PT Web Gap Finder

Portugal-focused company prospecting and website-gap analysis CLI.

The project finds Portuguese businesses from public/open sources, enriches them with evidence-backed contact and online-presence data, checks whether they have no website or a weak website, and exports prioritized lead lists for website creation/redesign outreach.

## What it does

The current MVP can run an end-to-end prospecting workflow:

```text
scan businesses → analyze websites → rank opportunities → write report
```

It currently uses OpenStreetMap / Overpass as the first discovery source and keeps provenance artifacts beside the exported leads.

## Quickstart

### 1. Install locally

From the repo root:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

If your system Python is externally managed, keep using the virtualenv commands above rather than installing into the system environment.

If pip reports a cache/download decoding error, retry without the local package cache:

```bash
python -m pip cache purge
PIP_NO_CACHE_DIR=1 python -m pip install -e '.[dev]'
```

### 2. Run a complete campaign

Use `run` for the full one-command workflow:

```bash
pt-web-gap-finder run \
  --place porto \
  --category restaurants \
  --limit 25 \
  --output-dir outputs/porto-restaurants
```

This writes:

```text
outputs/porto-restaurants/
  leads.csv
  leads.json
  evidence.jsonl
  analyzed.csv
  analyzed.json
  analyzed-evidence.jsonl
  report.md
```

Open `report.md` first. Use the CSV/JSON files for spreadsheet or CRM imports, and use the evidence ledgers to inspect provenance.

## Common campaign examples

```bash
# Restaurants, cafes, bars, and fast food in Porto
pt-web-gap-finder run --place porto --category restaurants --limit 50 --output-dir outputs/porto-restaurants

# Health-related local businesses in Lisbon
pt-web-gap-finder run --place lisboa --category health --limit 50 --output-dir outputs/lisboa-health

# Local services in Braga
pt-web-gap-finder run --place braga --category local-services --limit 50 --output-dir outputs/braga-local-services

# Food and drink businesses in Coimbra
pt-web-gap-finder run --place coimbra --category food-drink --limit 50 --output-dir outputs/coimbra-food-drink
```

## Places

You can use `--place` instead of manually typing bbox coordinates.

Initial Portugal presets:

- `porto`
- `lisboa`
- `braga`
- `coimbra`
- `faro`

Useful aliases include:

- `oporto`
- `lisbon`
- `porto-centro`
- `lisboa-centro`
- `braga-centro`
- `coimbra-centro`
- `faro-centro`

Advanced users can still pass a manual bounding box:

```bash
pt-web-gap-finder run \
  --bbox -8.69,41.12,-8.55,41.19 \
  --category restaurant \
  --limit 25 \
  --output-dir outputs/custom-porto-bbox
```

Use either `--place` or `--bbox`, not both.

## Categories and bundles

Single categories:

- `restaurant`
- `cafe`
- `bar`
- `fast_food`
- `dentist`
- `pharmacy`
- `clinic`
- `hairdresser`
- `real_estate`
- `gym`
- `bakery`
- `car_repair`

Campaign bundles:

- `restaurants` → `restaurant`, `cafe`, `bar`, `fast_food`
- `food-drink` → `restaurant`, `cafe`, `bar`, `fast_food`, `bakery`
- `health` → `dentist`, `pharmacy`, `clinic`
- `local-services` → `hairdresser`, `real_estate`, `gym`, `bakery`, `car_repair`

Bundle runs execute multiple category scans, deduplicate leads, and merge results in a round-robin order so small limits still include multiple business types.

## Individual commands

Use these when you want to inspect each stage separately.

### Scan businesses

```bash
pt-web-gap-finder scan \
  --place porto \
  --category restaurants \
  --limit 25 \
  --output outputs/scan/leads.csv \
  --json-output outputs/scan/leads.json \
  --evidence-output outputs/scan/evidence.jsonl
```

### Analyze websites

```bash
pt-web-gap-finder analyze-sites \
  --input outputs/scan/leads.json \
  --output outputs/scan/analyzed.json \
  --csv-output outputs/scan/analyzed.csv \
  --evidence-output outputs/scan/analyzed-evidence.jsonl
```

The analyzer checks homepage signals such as:

- reachability
- HTTP status
- redirect/final URL
- HTTPS usage
- page title
- meta description
- mobile viewport tag
- contact signals such as email, phone, and contact links

### Generate a report

```bash
pt-web-gap-finder report \
  --input outputs/scan/analyzed.json \
  --output outputs/scan/report.md \
  --top 25
```

The report groups and ranks opportunities by website gap, priority, evidence-backed reasons, and pitch angle.

## Output files

- `leads.csv` / `leads.json`: discovered businesses before website analysis
- `evidence.jsonl`: source evidence for discovered business facts
- `analyzed.csv` / `analyzed.json`: leads after website quality analysis and rescoring
- `analyzed-evidence.jsonl`: evidence after adding website-analysis findings
- `report.md`: human-readable prospecting report

## Interpreting results

The tool is designed to help prioritize outreach, not to make absolute claims.

Important caveat: a missing website tag in OpenStreetMap means “no website found in this source,” not “the company definitely has no website.” Use the evidence ledger and report reasons before contacting a business.

Typical high-value opportunities are:

- no website found in available evidence
- broken or unreachable website
- weak website signals, such as no HTTPS, no title, no mobile viewport, missing contact signals, or missing meta description
- social-only presence without an owned website

## Development

Run tests and lint:

```bash
. .venv/bin/activate
pytest -q
ruff check .
```

Useful small smoke run:

```bash
pt-web-gap-finder run \
  --place porto \
  --category restaurants \
  --limit 4 \
  --output-dir outputs/smoke-porto-restaurants
```

## Repository layout

```text
pt-web-gap-finder/
  docs/
  src/pt_web_gap_finder/
    categories.py
    cli.py
    config.py
    models.py
    places.py
    report.py
    site_analysis.py
    normalization/
    output/
    scoring/
    sources/
  tests/
```

## Legal and ethical default

This project is intended to use public/open/official sources and allowed APIs. It should not scrape restricted platforms, collect private personal contacts, or claim certainty where the evidence is incomplete.

When using OpenStreetMap-derived data, respect the OpenStreetMap license and attribution requirements.
