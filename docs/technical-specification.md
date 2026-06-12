# PT Web Gap Finder — Technical Specification

Date: 2026-06-12
Status: draft v0.1

## 1. Goal

Build a Python CLI that discovers Portuguese companies/businesses from public, open, and official sources, enriches them with verifiable online-presence evidence, evaluates website existence/quality, and exports a lead list for website creation/redesign opportunities.

The tool should optimize for **provenance and confidence**, not just volume. Every important field should be traceable to a source and timestamp.

## 2. Primary users

- Freelancers/agencies selling websites to Portuguese businesses.
- Researchers building regional business directories.
- Operators who want a repeatable, auditable prospecting workflow.

## 3. Non-goals for MVP

- Do not scrape Google Maps or other restricted platforms directly.
- Do not collect private personal data unrelated to business contact.
- Do not claim a company has no website with absolute certainty.
- Do not attempt nationwide exhaustive registry coverage in v0.1.
- Do not build a web app before the CLI and data model are stable.

## 4. MVP scope

### Inputs

- Country: default `PT`.
- Region filters:
  - municipality/concelho name;
  - district name;
  - bounding box;
  - optional latitude/longitude radius later.
- Category filter:
  - high-level vertical, e.g. `restaurant`, `dentist`, `hairdresser`, `real_estate`, `construction`, `clinic`, `gym`, `cafe`.
- Source filter:
  - MVP: `osm`.
  - Later: `turismo_portugal`, `ers`, `impic`, `base_gov`, `csv`.
- Limits and output paths.

### Outputs

- CSV lead table.
- JSON records.
- Markdown summary report.
- Evidence ledger JSONL.
- Later: SQLite database.

## 5. Data-source tiers

### Tier 1 — MVP source

#### OpenStreetMap / Overpass API

Use for discovery of local business entities.

Useful OSM tags:

- `name`
- `amenity`, `shop`, `office`, `craft`, `tourism`, `healthcare`, `leisure`
- `addr:*`
- `phone`, `contact:phone`
- `email`, `contact:email`
- `website`, `contact:website`, `url`
- `facebook`, `contact:facebook`, `instagram`, `contact:instagram`
- `opening_hours`

Strengths:

- Open, queryable, good coverage for local businesses.
- Website tag absence is an actionable signal.

Limitations:

- Missing website tag is not proof of no website.
- Completeness varies by municipality/sector.
- ODbL attribution and share-alike obligations must be respected.

### Tier 2 — official/regulated sources

Add adapters after OSM works:

- Turismo de Portugal / tourism registries.
- ERS health providers.
- IMPIC construction/real-estate entities.
- BASE.gov.pt public procurement suppliers.
- Banco de Portugal / ASF / CMVM for regulated sectors.
- dados.gov.pt datasets when they contain entity-level resources.

### Tier 3 — search/enrichment APIs

Allowed API-based discovery only:

- Brave Search API.
- Bing Web Search API.
- Google Custom Search API, if configured.
- SerpAPI, if accepted.
- WHOIS/RDAP where useful.

## 6. Core data model

### CompanyLead

```python
class CompanyLead:
    id: str
    name: str
    normalized_name: str
    country: str = "PT"
    sector: str | None
    category: str | None
    legal_name: str | None
    tax_id: str | None
    source_ids: list[str]
    address: Address | None
    contacts: Contacts
    online_presence: OnlinePresence
    website_analysis: WebsiteAnalysis | None
    scores: LeadScores
    evidence: list[EvidenceItem]
    retrieved_at: datetime
```

### Address

- `street`
- `postal_code`
- `locality`
- `municipality`
- `district`
- `lat`
- `lon`
- `raw`

### Contacts

- `phone`
- `mobile`
- `email`
- `contact_url`
- `social_profiles`

### OnlinePresence

- `website_found: bool | None`
- `website_url`
- `website_discovery_method`
- `domain_confidence: float`
- `social_only: bool`
- `search_candidates: list[WebsiteCandidate]`

### WebsiteAnalysis

- `http_status`
- `final_url`
- `https`
- `reachable`
- `redirect_chain`
- `title`
- `meta_description_present`
- `mobile_viewport_present`
- `contact_signals`
- `lighthouse` later
- `cms_detected` later
- `broken_link_count` later

### EvidenceItem

Every non-trivial value must be backed by evidence:

- `field`
- `value`
- `source_name`
- `source_type`: `open_data`, `official_registry`, `search_api`, `company_website`, `derived`
- `source_url`
- `retrieved_at`
- `confidence`: `high`, `medium`, `low`
- `notes`

## 7. Pipeline architecture

```text
Source adapters
  -> normalization
  -> deduplication
  -> enrichment
  -> website analysis
  -> scoring
  -> export/report
```

### 7.1 Source adapters

Each adapter returns `RawBusinessRecord` objects plus evidence.

Interface:

```python
class SourceAdapter(Protocol):
    name: str
    async def fetch(self, query: SourceQuery) -> list[RawBusinessRecord]: ...
```

### 7.2 Normalization

Normalize:

- names: trim, collapse whitespace, remove noisy suffixes only in secondary normalized field;
- URLs: force scheme, lower host, remove tracking params;
- phones: keep original and E.164-ish normalized form;
- emails: lower-case domain/local cautiously;
- addresses: preserve raw fields, do not over-normalize official text.

### 7.3 Deduplication

Prefer stable keys in this order:

1. tax ID / NIPC if available;
2. exact normalized website domain;
3. normalized phone;
4. normalized name + municipality;
5. geospatial proximity + similar name.

Deduplication should preserve all source records in `evidence` rather than deleting them.

### 7.4 Website discovery

Methods:

1. source-provided website field;
2. allowed search API query: `"<business name>" "<municipality>" site:.pt`;
3. domain candidate guessing as low-confidence only;
4. social-profile discovery.

Website absence classifications:

- `source_missing_website`: source had no website field;
- `search_no_candidate`: search returned no plausible official site;
- `social_only`: social profile found but no website;
- `uncertain`: ambiguous candidates exist;
- `found`: official-looking website found.

### 7.5 Website health analysis

MVP checks:

- URL reachable within timeout;
- HTTP status;
- HTTPS used;
- final URL after redirects;
- HTML title present;
- meta description present;
- mobile viewport present;
- visible phone/email/contact keywords;
- obvious parked/under-construction markers.

Later checks:

- Lighthouse performance/SEO/accessibility;
- broken link crawl;
- technology/CMS detection;
- visual/design heuristics;
- structured data;
- cookie/privacy compliance signals.

## 8. Lead scoring

Score should be explainable. Store both numeric score and reasons.

Initial score rules:

- no website found: +45
- only social profile found: +30
- site unreachable: +40
- no HTTPS: +20
- no mobile viewport: +20
- missing title/meta basics: +10
- no contact signal on homepage: +10
- high-value/service sector: +10
- official/regulated source corroboration: +15
- low identity confidence: -30
- good reachable website with basics: -40

Priority bands:

- `hot`: 80–100
- `warm`: 55–79
- `low`: 25–54
- `ignore`: below 25

## 9. CLI commands

See `docs/python-cli-plan.md` for full command design.

## 10. Compliance and safety

- Respect source licenses and attribution requirements.
- Respect robots.txt/terms for direct website crawling.
- Rate-limit all external requests.
- Use configured APIs where platforms require API access.
- Store business contact only; avoid unnecessary personal data.
- Keep evidence, confidence, and retrieved timestamp with outputs.
- Provide opt-out/remove mechanism before any hosted product.

## 11. Definition of done for MVP

- Can fetch OSM businesses for one Portuguese municipality and category.
- Can export CSV/JSON with evidence.
- Can detect source-provided missing websites.
- Can analyze source-provided/found URLs with basic HTTP/HTML checks.
- Can generate lead scores with reasons.
- Has tests for models, scoring, OSM query building, URL normalization, and CSV export.
- README includes working examples.
