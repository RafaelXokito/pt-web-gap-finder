# Data Sources

This file tracks candidate sources, expected fields, license/terms notes, and implementation status.

## MVP

### OpenStreetMap / Overpass API

- Status: planned first adapter.
- Source type: open geodata.
- Useful for: local business discovery.
- License: ODbL; attribution required.
- Key fields: name, category tags, address tags, phone/email/website/contact tags, coordinates.
- Confidence: medium unless corroborated by another source.
- Caveat: missing website tag is not proof of no website.

## Official/regulated source candidates

### dados.gov.pt — Empresas dataset

- Status: inspected.
- Finding: official IRN dataset discovered, but it appears aggregate/statistical rather than entity-level.
- Use: market context, not MVP lead discovery.
- API page: `https://dados.gov.pt/api/1/datasets/empresas/`

### Turismo de Portugal registries

- Status: candidate.
- Use: accommodation, tourism enterprises, travel-related businesses.
- Next step: review official access method, terms, and downloadable data/API availability.

### ERS health providers

- Status: candidate.
- Use: clinics, medical/dental providers, diagnostics.
- Next step: review public registry access and allowed reuse.

### IMPIC

- Status: candidate.
- Use: construction and real-estate mediation entities.
- Next step: identify official export/API and license/terms.

### BASE.gov.pt

- Status: candidate.
- Use: suppliers active in public procurement.
- Next step: inspect API/export fields and company identifiers.

## Search APIs

Preferred search providers should be API-based and configurable:

- Brave Search API
- Bing Web Search API
- Google Custom Search API
- SerpAPI

Raw scraping of restricted search/map platforms should be avoided unless terms and legal review allow it.
