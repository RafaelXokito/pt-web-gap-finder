from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from pt_web_gap_finder.models import CompanyLead

CSV_FIELDS = [
    "id",
    "name",
    "category",
    "municipality",
    "district",
    "phone",
    "email",
    "website_found",
    "website_url",
    "website_reachable",
    "website_http_status",
    "website_final_url",
    "website_https",
    "website_title",
    "meta_description_present",
    "mobile_viewport_present",
    "contact_signals",
    "opportunity_score",
    "confidence_score",
    "priority",
    "reasons",
    "evidence_count",
]


def _row_for_lead(lead: CompanyLead) -> dict[str, str | int | bool | None]:
    address = lead.address
    contacts = lead.contacts
    scores = lead.scores
    analysis = lead.website_analysis
    return {
        "id": lead.id,
        "name": lead.name,
        "category": lead.category or "",
        "municipality": address.municipality if address and address.municipality else "",
        "district": address.district if address and address.district else "",
        "phone": contacts.phone or contacts.mobile or "",
        "email": contacts.email or "",
        "website_found": lead.online_presence.website_found,
        "website_url": lead.online_presence.website_url or "",
        "website_reachable": analysis.reachable if analysis else "",
        "website_http_status": analysis.http_status if analysis and analysis.http_status else "",
        "website_final_url": analysis.final_url if analysis and analysis.final_url else "",
        "website_https": analysis.https if analysis else "",
        "website_title": analysis.title if analysis and analysis.title else "",
        "meta_description_present": analysis.meta_description_present if analysis else "",
        "mobile_viewport_present": analysis.mobile_viewport_present if analysis else "",
        "contact_signals": "; ".join(analysis.contact_signals) if analysis else "",
        "opportunity_score": scores.opportunity_score,
        "confidence_score": scores.confidence_score,
        "priority": scores.priority,
        "reasons": "; ".join(scores.reasons),
        "evidence_count": len(lead.evidence),
    }


def write_leads_csv(leads: Iterable[CompanyLead], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for lead in leads:
            writer.writerow(_row_for_lead(lead))
