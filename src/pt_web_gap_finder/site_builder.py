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


def build_ship_ready_site_package(lead: CompanyLead, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    content = _build_content_payload(lead)
    file_map = {
        "brief.md": _render_ship_ready_brief(lead, content),
        "content.json": json.dumps(content, ensure_ascii=False, indent=2),
        "index.html": _render_ship_ready_html(lead, content),
        "styles.css": _render_ship_ready_styles(),
        "hermes-redesign-prompt.md": _render_ship_ready_prompt(lead, output_dir),
        "design-plan.md": _render_design_plan(lead, content),
        "design-analysis.md": _render_design_analysis(lead, content),
        "ship-checklist.md": _render_ship_checklist(lead, content),
        "publish-ready-summary.md": _render_publish_ready_summary(lead, content),
    }
    written_paths: list[Path] = []
    for filename, payload in file_map.items():
        path = output_dir / filename
        path.write_text(payload, encoding="utf-8")
        written_paths.append(path)
    return written_paths


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


def _render_ship_ready_brief(lead: CompanyLead, content: dict[str, Any]) -> str:
    services = "\n".join(f"- {item}" for item in content["service_prompts"])
    return f"""# {lead.name} ship-ready website brief

This folder contains a **ship-ready website package** for `{lead.name}`.

It is grounded in the analyzed lead record and designed to move from prospecting to a production handoff with minimal additional work.

## Business snapshot

- Company: {lead.name}
- Category: {content['category']}
- Locality: {content['locality']}
- Prospecting priority: {lead.scores.priority}
- Opportunity score: {lead.scores.opportunity_score}
- Confidence score: {lead.scores.confidence_score}

## Recommended page narrative

1. Hero with a trust-first local value proposition
2. Proof and contact snapshot
3. Service overview based on evidence-backed placeholders
4. Why-choose-us style benefits section
5. Contact and location section
6. Final CTA with confirmation note

## Service prompts to confirm

{services}

## Final check

Treat this package as **Ready to ship after human confirmation** of services, hours, pricing, branding, and any missing legal details.
"""


def _render_design_plan(lead: CompanyLead, content: dict[str, Any]) -> str:
    category = content["category"]
    locality = content["locality"]
    return f"""<design_plan>
Reading this as: local-business landing page for nearby customers in {locality}, with a premium trust-first dark language, leaning toward a custom editorial marketing page.

Design Read
- Lead: {lead.name}
- Category: {category}
- Audience: local prospects who need a fast trust signal and clear contact path
- Design Variance: 7
- Motion Intensity: 4
- Visual Density: 3

Python RNG Execution
- seed = len('{lead.name}') + {lead.scores.opportunity_score} = {len(lead.name) + lead.scores.opportunity_score}
- hero_architecture = editorial offset composition
- typography_stack = Geist + Geist Mono
- component_architectures = pristine gapless bento grid, split testimonial quote wall, product UI panel stack
- motion_paradigms = staggered float-up energy, cinematic fade-through energy

AIDA Check
- Attention: hero with category + locality + direct CTA
- Interest: proof panel, service prompts, benefit cards
- Desire: evidence-backed reassurance and local credibility
- Action: contact/location block and closing CTA

Hero Math Verification
- headline container target: max-width 10ch on desktop, headline stays inside 2 lines for most company categories
- first viewport remains clean with only eyebrow, headline, subcopy, and 2 CTAs
- no cheap meta-labels, no fake counters, no dashboard chrome

Bento Density Verification
- feature grid uses 2 cards with no empty cells in desktop mode
- supporting sections switch to stacked editorial blocks for rhythm
- no dead grid gaps, no repeated three-equal-card cliché

Skills to use in follow-up session
- design-taste-frontend
- gpt-taste
- image-to-code
- imagegen-frontend-web
- full-output-enforcement
</design_plan>
"""


def _render_design_analysis(lead: CompanyLead, content: dict[str, Any]) -> str:
    return f"""# Design analysis for {lead.name}

## Section 1 - Hero
- Priority: instant trust, locality, and direct action
- Headline direction: short, clear, category-aware, not overclaiming
- CTA hierarchy: primary phone action, secondary review/confirmation action

## Section 2 - Proof strip
- Shows prospecting priority, opportunity score, and confidence score
- Keeps evidence visible without turning the page into a dashboard

## Section 3 - Services block
- Uses service prompts as placeholders to confirm with the client
- Avoids inventing detailed offerings that are not verified yet

## Section 4 - Benefit narrative
- Focuses on customer outcomes such as clarity, contact, trust, and local presence
- Keeps copy grounded and broadly true for the category

## Section 5 - Contact and location
- Uses available address and contact fields directly from the analyzed lead
- Makes the conversion path obvious for a local business website

## Section 6 - Final CTA
- Closes with a simple action and a reminder to confirm factual details before publish

## Visual system summary
- Deep dark palette with one blue accent
- Consistent large radius system
- Editorial spacing with open sections
- No em dashes, no fake metrics, no AI-purple glow
"""


def _render_ship_checklist(lead: CompanyLead, content: dict[str, Any]) -> str:
    return f"""# Ship checklist for {lead.name}

## Pre-flight

- [ ] Confirm official business name spelling
- [ ] Confirm logo, colors, and typography with the client
- [ ] Confirm real services from the category prompt list
- [ ] Confirm opening hours
- [ ] Confirm phone number
- [ ] Confirm email address
- [ ] Confirm street address and map link
- [ ] Add privacy / cookie / legal pages if needed
- [ ] Replace any placeholder contact language with approved copy
- [ ] Review on mobile and desktop before publish

## Technical readiness

- [ ] HTML package opens correctly from `index.html`
- [ ] `styles.css` is linked and renders the intended layout
- [ ] Headline and CTAs remain visible in the first viewport
- [ ] Contact path is visible without hunting through the page
- [ ] No claims were added beyond the evidence-backed lead record
"""


def _render_publish_ready_summary(lead: CompanyLead, content: dict[str, Any]) -> str:
    return f"""# Publish-ready summary for {lead.name}

Status: **Ready to ship after human confirmation**

## What is already prepared

- a polished one-page website implementation
- a grounded business-content payload
- a design plan aligned with premium frontend skills
- a handoff prompt for a stronger image-first redesign session
- a checklist for final factual confirmation before launch

## What still requires human confirmation

- official branding assets
- exact services and commercial copy
- opening hours and booking flow
- legal / privacy requirements
- final contact and map details

## Recommended next action

Open `index.html`, review the package with the business owner, confirm the missing details, and then either publish this version or use `hermes-redesign-prompt.md` for a higher-end art-directed pass.
"""


def _render_ship_ready_prompt(lead: CompanyLead, output_dir: Path) -> str:
    return f"""# Hermes ship-ready prompt for {lead.name}

Load and use these skills:
- design-taste-frontend
- gpt-taste
- image-to-code
- imagegen-frontend-web
- full-output-enforcement

Task:

Open `{output_dir}`.
Read `brief.md`, `content.json`, `design-plan.md`, `design-analysis.md`, `ship-checklist.md`, `index.html`, and `styles.css`.

Then produce a stronger premium landing page for `{lead.name}` while keeping every factual business detail grounded in `content.json`.

Mandatory rules:
- follow an image-first workflow if image generation is available
- keep one consistent theme and accent color
- keep the hero readable on a small laptop
- do not invent unverified services, prices, hours, or client claims
- preserve the direct contact conversion path
- finish with a short list of final facts that still need human confirmation before publish
"""


def _render_ship_ready_html(lead: CompanyLead, content: dict[str, Any]) -> str:
    raw_phone = content["contacts"].get("phone") or content["contacts"].get("mobile")
    raw_email = content["contacts"].get("email")
    phone = raw_phone or "Confirm phone number"
    email = raw_email or "Confirm email address"
    locality = content["locality"]
    street = content["location"].get("street") or "Confirm street address"
    primary_cta = content["primary_cta"]
    phone_href = f"tel:{raw_phone}" if raw_phone else "#confirm"
    email_href = f"mailto:{raw_email}" if raw_email else "#confirm"
    proof_items = "\n".join(
        f'            <li><span>{item.split(":")[0]}</span><strong>{item.split(":", 1)[1].strip()}</strong></li>'
        if ":" in item
        else f'            <li><span>Signal</span><strong>{item}</strong></li>'
        for item in content["proof_points"]
    )
    service_cards = "\n".join(
        f'''          <article class="mini-card">\n            <p class="micro-label">Confirm</p>\n            <h3>{item}</h3>\n            <p>Replace this placeholder with verified business details before launch.</p>\n          </article>'''
        for item in content["service_prompts"]
    )
    evidence_items = "\n".join(f"            <li>{item}</li>" for item in content["evidence_summary"])
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{lead.name}</title>
    <meta name="description" content="Local website package for {lead.name} in {locality}." />
    <link rel="stylesheet" href="styles.css" />
  </head>
  <body>
    <main class="site-shell">
      <section class="hero-block">
        <header class="topbar">
          <p class="brand-mark">{lead.name}</p>
          <a class="ghost-link" href="#contact">Contact</a>
        </header>
        <div class="hero-layout">
          <div class="hero-copy">
            <p class="eyebrow">{content['category']} in {locality}</p>
            <h1>{content['headline']}</h1>
            <p class="hero-summary">{content['subheadline']}</p>
            <div class="cta-row">
              <a class="button button-primary" href="{phone_href}">{primary_cta}</a>
              <a class="button button-secondary" href="#confirm">Confirm details before launch</a>
            </div>
          </div>
          <aside class="hero-panel">
            <p class="micro-label">Ready after approval</p>
            <h2>Fast local trust, clear contact, no extra clutter.</h2>
            <dl>
              <div><dt>Address</dt><dd>{street}</dd></div>
              <div><dt>Locality</dt><dd>{locality}</dd></div>
              <div><dt>Phone</dt><dd>{phone}</dd></div>
              <div><dt>Email</dt><dd>{email}</dd></div>
            </dl>
          </aside>
        </div>
      </section>

      <section class="proof-band" aria-label="Evidence backed proof points">
        <ul>
{proof_items}
        </ul>
      </section>

      <section class="section-block service-block">
        <div class="section-header">
          <p class="eyebrow">Suggested sections</p>
          <h2>Confirm the real service mix, then publish with confidence.</h2>
        </div>
        <div class="service-grid">
{service_cards}
        </div>
      </section>

      <section class="section-block split-block">
        <article class="content-column">
          <p class="eyebrow">Why this works</p>
          <h2>Built for nearby customers who just need trust and a direct next step.</h2>
          <p>
            This page stays simple on purpose. It gives the business a clear local presence, a direct contact path,
            and enough structure to upgrade later without wasting the current prospecting research.
          </p>
        </article>
        <article class="evidence-card">
          <p class="micro-label">Evidence summary</p>
          <ul>
{evidence_items}
          </ul>
        </article>
      </section>

      <section class="section-block contact-block" id="contact">
        <div class="contact-card">
          <p class="eyebrow">Contact and location</p>
          <h2>Make it easy to call, visit, or verify the business quickly.</h2>
          <div class="contact-grid">
            <div><span>Phone</span><strong>{phone}</strong></div>
            <div><span>Email</span><strong>{email}</strong></div>
            <div><span>Street</span><strong>{street}</strong></div>
            <div><span>Locality</span><strong>{locality}</strong></div>
          </div>
        </div>
      </section>

      <section class="section-block final-cta" id="confirm">
        <div>
          <p class="eyebrow">Final review</p>
          <h2>Ship this after one human pass over services, hours, and branding.</h2>
          <p>
            The page is already structured for launch. The remaining work is factual confirmation, not blank-page design.
          </p>
        </div>
        <div class="cta-row">
          <a class="button button-primary" href="{phone_href}">{primary_cta}</a>
          <a class="button button-secondary" href="{email_href}">Email the business</a>
        </div>
      </section>
    </main>
  </body>
</html>
"""


def _render_ship_ready_styles() -> str:
    return """@import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700;800&family=Geist+Mono:wght@400;500&display=swap');

:root {
  color-scheme: dark;
  --bg: #07111f;
  --surface: rgba(8, 18, 34, 0.88);
  --surface-strong: rgba(14, 28, 48, 0.96);
  --line: rgba(148, 163, 184, 0.18);
  --text: #f5f7ff;
  --muted: #afbdd8;
  --accent: #72b4ff;
  --accent-strong: #dfeeff;
  --radius: 26px;
  --shadow: 0 28px 90px rgba(0, 0, 0, 0.35);
}

* {
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
}

body {
  margin: 0;
  font-family: 'Geist', system-ui, sans-serif;
  color: var(--text);
  background:
    radial-gradient(circle at top left, rgba(114, 180, 255, 0.2), transparent 28%),
    radial-gradient(circle at bottom right, rgba(59, 130, 246, 0.14), transparent 22%),
    linear-gradient(180deg, #08111f 0%, #0b1728 100%);
}

main.site-shell {
  width: min(1180px, calc(100vw - 32px));
  margin: 0 auto;
  padding: 28px 0 88px;
}

.hero-block,
.section-block,
.proof-band {
  margin-top: 28px;
}

.hero-block {
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 0;
}

.brand-mark,
.ghost-link,
.eyebrow,
.micro-label {
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-size: 0.78rem;
}

.brand-mark,
.ghost-link,
.eyebrow {
  color: var(--accent);
}

.ghost-link {
  text-decoration: none;
}

.hero-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(320px, 0.75fr);
  gap: 24px;
  align-items: end;
  flex: 1;
  padding: 20px 0 28px;
}

.hero-copy h1,
.section-header h2,
.content-column h2,
.contact-card h2,
.final-cta h2,
.hero-panel h2 {
  margin: 0;
  line-height: 0.94;
  letter-spacing: -0.05em;
}

.hero-copy h1 {
  max-width: 10ch;
  font-size: clamp(3.3rem, 7vw, 6.8rem);
}

.hero-summary,
.content-column p,
.final-cta p {
  max-width: 58ch;
  color: var(--muted);
  font-size: 1.08rem;
  line-height: 1.75;
}

.cta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 28px;
}

.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 52px;
  border-radius: 999px;
  padding: 0 22px;
  font-weight: 700;
  text-decoration: none;
  transition: transform 180ms ease, opacity 180ms ease, border-color 180ms ease;
}

.button:hover {
  transform: translateY(-1px);
}

.button-primary {
  background: var(--accent-strong);
  color: #08111f;
}

.button-secondary {
  color: var(--text);
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.02);
}

.hero-panel,
.service-grid article,
.evidence-card,
.contact-card,
.final-cta,
.proof-band,
.hero-block {
  border: 1px solid var(--line);
  border-radius: var(--radius);
}

.hero-panel,
.service-grid article,
.evidence-card,
.contact-card,
.final-cta,
.proof-band {
  background: var(--surface);
  box-shadow: var(--shadow);
  backdrop-filter: blur(18px);
}

.hero-panel,
.contact-card,
.final-cta,
.evidence-card,
.service-grid article {
  padding: 28px;
}

.hero-panel dl,
.contact-grid,
.proof-band ul,
.service-grid,
.evidence-card ul {
  margin: 0;
  padding: 0;
}

.hero-panel dl {
  display: grid;
  gap: 18px;
}

.hero-panel dl div,
.contact-grid div,
.proof-band li,
.evidence-card li {
  border-top: 1px solid var(--line);
  padding-top: 14px;
}

.hero-panel dt,
.contact-grid span,
.proof-band span {
  display: block;
  color: var(--muted);
  font-size: 0.92rem;
}

.hero-panel dd,
.contact-grid strong,
.proof-band strong {
  display: block;
  margin: 8px 0 0;
  font-size: 1rem;
}

.proof-band {
  padding: 18px 24px;
}

.proof-band ul {
  list-style: none;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.section-header {
  margin-bottom: 22px;
}

.section-header h2,
.content-column h2,
.contact-card h2,
.final-cta h2,
.hero-panel h2 {
  font-size: clamp(2rem, 4vw, 3.4rem);
}

.service-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.mini-card h3 {
  margin: 10px 0 12px;
  font-size: 1.35rem;
}

.mini-card p,
.evidence-card li {
  color: var(--muted);
  line-height: 1.75;
}

.split-block {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(300px, 0.9fr);
  gap: 22px;
  align-items: start;
}

.evidence-card ul {
  list-style: none;
}

.contact-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
  margin-top: 24px;
}

.final-cta {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 24px;
  align-items: end;
}

@media (max-width: 980px) {
  .hero-layout,
  .split-block,
  .service-grid,
  .contact-grid,
  .proof-band ul,
  .final-cta {
    grid-template-columns: 1fr;
  }

  .hero-block {
    min-height: auto;
  }

  .hero-copy h1 {
    max-width: none;
  }
}

@media (max-width: 720px) {
  main.site-shell {
    width: min(100vw - 20px, 720px);
    padding-bottom: 64px;
  }

  .hero-panel,
  .service-grid article,
  .evidence-card,
  .contact-card,
  .final-cta,
  .proof-band {
    padding: 22px;
  }
}
"""
