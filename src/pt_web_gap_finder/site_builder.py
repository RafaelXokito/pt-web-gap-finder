from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from pt_web_gap_finder.models import CompanyLead

CATEGORY_HEADLINES = {
    "hairdresser": "A calmer, more credible web presence for local clients.",
    "barber": "A calmer, more credible web presence for local clients.",
    "barbershop": "A calmer, more credible web presence for local clients.",
    "restaurant": "A clean local website that helps nearby customers choose you faster.",
    "cafe": "A simple local website that makes your menu, location, and contact easy to find.",
    "bakery": "A welcoming local website that helps customers find your products and location.",
    "car_repair": "A trust-first local website that makes services, contact, and location easy to find.",
}

CATEGORY_CTA = {
    "hairdresser": "Call to book",
    "barber": "Call to book",
    "barbershop": "Call to book",
    "restaurant": "See location and contact",
    "cafe": "See location and contact",
    "bakery": "See location and contact",
    "car_repair": "Call for service",
}

CATEGORY_SERVICE_PROMPTS = {
    "hairdresser": ["Core services", "Booking instructions", "Opening hours"],
    "barber": ["Core services", "Booking instructions", "Opening hours"],
    "barbershop": ["Core services", "Booking instructions", "Opening hours"],
    "restaurant": ["Menu highlights", "Reservation/contact flow", "Opening hours"],
    "cafe": ["Menu highlights", "Location and hours", "Contact details"],
    "bakery": ["Popular products", "Custom orders", "Opening hours"],
    "car_repair": ["Main repair services", "Emergency/contact flow", "Opening hours"],
}


def select_site_lead(leads: list[CompanyLead], lead_id: str | None = None) -> CompanyLead:
    if not leads:
        raise ValueError("no leads available")
    if lead_id:
        for lead in leads:
            if lead.id == lead_id:
                return lead
        raise ValueError(f"lead id not found: {lead_id}")
    ranked = sorted(
        leads,
        key=lambda lead: (
            -lead.scores.opportunity_score,
            -lead.scores.confidence_score,
            lead.name.casefold(),
        ),
    )
    return ranked[0]


def build_site_package(lead: CompanyLead, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    content = _build_content_payload(lead)
    brief_path = output_dir / "brief.md"
    content_path = output_dir / "content.json"
    html_path = output_dir / "index.html"
    styles_path = output_dir / "styles.css"
    prompt_path = output_dir / "hermes-redesign-prompt.md"

    brief_path.write_text(_render_brief(lead, content), encoding="utf-8")
    content_path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    styles_path.write_text(_render_styles(), encoding="utf-8")
    html_path.write_text(_render_html(lead, content), encoding="utf-8")
    prompt_path.write_text(_render_redesign_prompt(lead, output_dir), encoding="utf-8")
    return [brief_path, content_path, html_path, styles_path, prompt_path]


def default_site_output_dir(base_dir: Path, lead: CompanyLead) -> Path:
    slug = slugify(lead.name)
    return base_dir / slug


def slugify(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )
    normalized = re.sub(r"[^a-z0-9]+", "-", ascii_value.casefold()).strip("-")
    return normalized or "company-site"


def _build_content_payload(lead: CompanyLead) -> dict[str, Any]:
    locality = (lead.address.locality if lead.address else None) or (lead.address.municipality if lead.address else None) or "Portugal"
    district = (lead.address.district if lead.address else None) or "Portugal"
    category = lead.category or "local business"
    evidence_summary = [
        reason for reason in lead.scores.reasons if reason
    ] or ["Prospecting output suggests this business may benefit from a stronger official web presence."]
    return {
        "company_name": lead.name,
        "category": category,
        "locality": locality,
        "district": district,
        "headline": CATEGORY_HEADLINES.get(category, "A clearer local website that helps nearby customers trust and contact the business faster."),
        "subheadline": (
            f"Starter site package for {lead.name} in {locality}. All business details should be confirmed before publishing."
        ),
        "primary_cta": CATEGORY_CTA.get(category, "Get in touch"),
        "secondary_cta": "Confirm details before launch",
        "contacts": {
            "phone": lead.contacts.phone,
            "mobile": lead.contacts.mobile,
            "email": lead.contacts.email,
            "website": lead.online_presence.website_url,
        },
        "location": {
            "street": lead.address.street if lead.address else None,
            "postal_code": lead.address.postal_code if lead.address else None,
            "locality": lead.address.locality if lead.address else None,
            "municipality": lead.address.municipality if lead.address else None,
            "district": lead.address.district if lead.address else None,
        },
        "site_goal": "Create an evidence-backed website starter that can be reviewed and polished before any public launch.",
        "proof_points": [
            f"Prospecting priority: {lead.scores.priority}",
            f"Opportunity score: {lead.scores.opportunity_score}",
            f"Confidence score: {lead.scores.confidence_score}",
        ],
        "evidence_summary": evidence_summary,
        "service_prompts": CATEGORY_SERVICE_PROMPTS.get(category, ["Core services", "Opening hours", "Preferred contact method"]),
        "required_confirmation": [
            "Confirm official brand colors, logo, and typography.",
            "Confirm real services, pricing, opening hours, and booking flow.",
            "Confirm every phone, email, and address detail before publishing.",
        ],
    }


def _render_brief(lead: CompanyLead, content: dict[str, Any]) -> str:
    location = content["locality"]
    category = content["category"]
    evidence = "\n".join(f"- {item}" for item in content["evidence_summary"])
    confirmations = "\n".join(f"- {item}" for item in content["required_confirmation"])
    return f"""# {lead.name} website brief

This folder contains an **evidence-backed website starter** for `{lead.name}`.

## Business snapshot

- Company: {lead.name}
- Category: {category}
- Locality: {location}
- Prospecting priority: {lead.scores.priority}
- Opportunity score: {lead.scores.opportunity_score}
- Confidence score: {lead.scores.confidence_score}

## Why this site starter exists

{evidence}

## What is included

- `content.json` with grounded business facts pulled from the prospecting record
- `index.html` as a clean starter landing page
- `styles.css` with a polished default visual system
- `hermes-redesign-prompt.md` to continue in another Hermes session with stronger frontend / image workflows

## Confirm before publishing

{confirmations}
"""


def _render_html(lead: CompanyLead, content: dict[str, Any]) -> str:
    services = "\n".join(
        f'          <li class="service-item">{service}</li>' for service in content["service_prompts"]
    )
    proof_points = "\n".join(
        f'          <li class="proof-item">{point}</li>' for point in content["proof_points"]
    )
    evidence = "\n".join(
        f'          <li>{item}</li>' for item in content["evidence_summary"]
    )
    phone = content["contacts"].get("phone") or content["contacts"].get("mobile") or "Confirm phone number"
    email = content["contacts"].get("email") or "Confirm email address"
    locality = content["locality"]
    street = content["location"].get("street") or "Confirm street address"
    category = content["category"]
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{lead.name}</title>
    <meta
      name="description"
      content="Starter website concept for {lead.name} in {locality}. Review all business details before launch."
    />
    <link rel="stylesheet" href="styles.css" />
  </head>
  <body>
    <main class="page-shell">
      <section class="hero">
        <div class="hero-copy">
          <p class="eyebrow">{category} in {locality}</p>
          <h1>{content["headline"]}</h1>
          <p class="subcopy">{content["subheadline"]}</p>
          <div class="cta-row">
            <a class="button button-primary" href="tel:{phone}">{content["primary_cta"]}</a>
            <a class="button button-secondary" href="#confirm">{content["secondary_cta"]}</a>
          </div>
        </div>
        <div class="hero-panel">
          <div class="panel-card">
            <p class="panel-label">Business details</p>
            <h2>{lead.name}</h2>
            <dl>
              <div><dt>Location</dt><dd>{locality}</dd></div>
              <div><dt>Address</dt><dd>{street}</dd></div>
              <div><dt>Phone</dt><dd>{phone}</dd></div>
              <div><dt>Email</dt><dd>{email}</dd></div>
            </dl>
          </div>
        </div>
      </section>

      <section class="section-grid">
        <article class="content-card">
          <p class="section-label">Suggested website sections</p>
          <ul class="service-list">
{services}
          </ul>
        </article>
        <article class="content-card accent-card">
          <p class="section-label">Prospecting signals</p>
          <ul class="proof-list">
{proof_points}
          </ul>
        </article>
      </section>

      <section class="section-stack">
        <article class="content-card wide-card">
          <p class="section-label">Evidence summary</p>
          <ul class="evidence-list">
{evidence}
          </ul>
        </article>
      </section>

      <section class="section-stack" id="confirm">
        <article class="content-card wide-card muted-card">
          <p class="section-label">Confirm before launch</p>
          <h2>Review every factual business detail before publishing.</h2>
          <p>
            This page is a starter package designed to speed up concepting and handoff. It is not a final live website.
          </p>
        </article>
      </section>
    </main>
  </body>
</html>
"""


def _render_styles() -> str:
    return """@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');

:root {
  color-scheme: dark;
  --bg: #0b1020;
  --panel: rgba(17, 24, 39, 0.82);
  --panel-strong: rgba(32, 44, 71, 0.92);
  --text: #eef2ff;
  --muted: #b9c3dd;
  --line: rgba(148, 163, 184, 0.24);
  --accent: #60a5fa;
  --accent-soft: rgba(96, 165, 250, 0.14);
  --radius: 22px;
  --shadow: 0 30px 80px rgba(0, 0, 0, 0.35);
}

* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: 'Manrope', system-ui, sans-serif;
  background:
    radial-gradient(circle at top left, rgba(96, 165, 250, 0.25), transparent 30%),
    radial-gradient(circle at bottom right, rgba(59, 130, 246, 0.2), transparent 28%),
    var(--bg);
  color: var(--text);
}
.page-shell {
  width: min(1200px, calc(100vw - 32px));
  margin: 0 auto;
  padding: 32px 0 80px;
}
.hero {
  min-height: 100dvh;
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 28px;
  align-items: center;
}
.hero-copy h1 {
  margin: 0;
  max-width: 12ch;
  font-size: clamp(3rem, 6vw, 5.6rem);
  line-height: 0.95;
  letter-spacing: -0.05em;
}
.eyebrow, .section-label, .panel-label {
  margin: 0 0 16px;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.14em;
  font-size: 0.75rem;
}
.subcopy {
  max-width: 58ch;
  color: var(--muted);
  font-size: 1.1rem;
  line-height: 1.7;
}
.cta-row {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  margin-top: 28px;
}
.button {
  text-decoration: none;
  border-radius: 999px;
  padding: 14px 20px;
  font-weight: 700;
}
.button-primary {
  background: var(--text);
  color: #0b1020;
}
.button-secondary {
  background: transparent;
  color: var(--text);
  border: 1px solid var(--line);
}
.hero-panel, .content-card {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: var(--panel);
  box-shadow: var(--shadow);
  backdrop-filter: blur(18px);
}
.panel-card, .content-card {
  padding: 28px;
}
.panel-card h2, .content-card h2 {
  margin: 0 0 18px;
  font-size: clamp(1.6rem, 3vw, 2.4rem);
}
.panel-card dl {
  display: grid;
  gap: 18px;
  margin: 0;
}
.panel-card div, .proof-item, .service-item, .evidence-list li {
  border-top: 1px solid var(--line);
  padding-top: 16px;
}
.panel-card dt {
  color: var(--muted);
  font-size: 0.92rem;
}
.panel-card dd {
  margin: 8px 0 0;
  font-size: 1rem;
}
.section-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 24px;
  margin-top: 32px;
}
.section-stack {
  margin-top: 24px;
}
.wide-card { padding: 32px; }
.accent-card {
  background: linear-gradient(160deg, rgba(37, 99, 235, 0.2), rgba(17, 24, 39, 0.92));
}
.muted-card {
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.95), rgba(17, 24, 39, 0.95));
}
.service-list, .proof-list, .evidence-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.service-item, .proof-item {
  font-size: 1.05rem;
}
.evidence-list li {
  color: var(--muted);
  line-height: 1.7;
}
@media (max-width: 900px) {
  .hero, .section-grid {
    grid-template-columns: 1fr;
  }
  .page-shell {
    width: min(100vw - 24px, 720px);
  }
  .hero {
    min-height: auto;
    padding-top: 48px;
  }
  .hero-copy h1 {
    max-width: none;
  }
}
"""


def _render_redesign_prompt(lead: CompanyLead, output_dir: Path) -> str:
    return f"""# Hermes follow-up prompt for {lead.name}

Use these skills in the new session:
- design-taste-frontend
- gpt-taste
- image-to-code

Task:

Open `{output_dir}`.
Read `brief.md`, `content.json`, `index.html`, and `styles.css`.

Then create a stronger premium redesign workflow for `{lead.name}` that remains grounded in the available business facts.

Requirements:
- keep all factual business details evidence-backed
- do not invent services, prices, or opening hours as final truth
- if design images are available, follow the image-first workflow before major frontend changes
- keep the first screen clean and readable on a small laptop
- avoid generic AI layouts and avoid overboxed nested cards
- preserve a simple conversion path for phone/contact

Deliverables:
1. improved visual direction summary
2. any extra design assets or prompts you need
3. upgraded frontend implementation
4. a short list of facts that still need human confirmation before publishing
"""
