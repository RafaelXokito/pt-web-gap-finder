from __future__ import annotations

from collections import Counter

from pt_web_gap_finder.models import CompanyLead


PRIORITY_ORDER = {"hot": 0, "warm": 1, "low": 2, "ignore": 3}


def classify_gap(lead: CompanyLead) -> str:
    analysis = lead.website_analysis
    if lead.online_presence.website_found is False:
        return "No website found"
    if analysis and "Browser/bot-protection challenge detected" in analysis.notes:
        return "Manual verification required"
    if analysis and analysis.reachable is False:
        return "Broken or unreachable website"
    if analysis and (
        analysis.https is False
        or analysis.mobile_viewport_present is False
        or analysis.meta_description_present is False
        or not analysis.contact_signals
    ):
        return "Weak website"
    if lead.online_presence.social_only:
        return "Social-only presence"
    if lead.online_presence.website_found is True:
        return "Website present"
    return "Unknown"


def pitch_angle_for_gap(gap_type: str) -> str:
    if gap_type == "No website found":
        return "Launch a credible local-business website with contacts, map, and service pages"
    if gap_type == "Broken or unreachable website":
        return "Repair trust-critical web presence before customers bounce or assume closure"
    if gap_type == "Weak website":
        return "Modernize the existing site for mobile, SEO snippets, HTTPS, and conversion contacts"
    if gap_type == "Social-only presence":
        return "Own the customer journey beyond social platforms with a lightweight official site"
    if gap_type == "Manual verification required":
        return "Manually review the site before outreach; automated checks hit browser protection"
    return "Monitor or enrich with more evidence before outreach"


def render_markdown_report(leads: list[CompanyLead], *, top: int = 50) -> str:
    ranked = sorted(
        leads,
        key=lambda lead: (
            PRIORITY_ORDER.get(lead.scores.priority, 99),
            -lead.scores.opportunity_score,
            -lead.scores.confidence_score,
            lead.name.lower(),
        ),
    )[:top]
    priority_counts = Counter(lead.scores.priority for lead in leads)
    gap_counts = Counter(classify_gap(lead) for lead in leads)

    lines = [
        "# Portugal Website Gap Finder Report",
        "",
        "## Summary",
        "",
        f"- Total leads analyzed: {len(leads)}",
        f"- Included in report: {len(ranked)}",
        f"- Hot: {priority_counts.get('hot', 0)}",
        f"- Warm: {priority_counts.get('warm', 0)}",
        f"- Low: {priority_counts.get('low', 0)}",
        f"- Ignore: {priority_counts.get('ignore', 0)}",
        "",
        "## Gap breakdown",
        "",
    ]
    for gap_type, count in gap_counts.most_common():
        lines.append(f"- {gap_type}: {count}")

    lines.extend(["", "## Top opportunities", ""])
    if not ranked:
        lines.append("No leads available.")
        return "\n".join(lines).rstrip() + "\n"

    for index, lead in enumerate(ranked, start=1):
        gap_type = classify_gap(lead)
        analysis = lead.website_analysis
        lines.extend(
            [
                f"### {index}. {lead.name}",
                "",
                f"- Priority: {lead.scores.priority}",
                f"- Opportunity score: {lead.scores.opportunity_score}",
                f"- Confidence score: {lead.scores.confidence_score}",
                f"- Category: {lead.category or 'unknown'}",
                f"- Gap type: {gap_type}",
                f"- Pitch angle: {pitch_angle_for_gap(gap_type)}",
                f"- Website: {lead.online_presence.website_url or 'not found'}",
            ]
        )
        if analysis:
            lines.extend(
                [
                    f"- Reachable: {_format_bool(analysis.reachable)}",
                    f"- HTTP status: {analysis.http_status or 'unknown'}",
                    f"- Final URL: {analysis.final_url or 'unknown'}",
                    f"- HTTPS: {_format_bool(analysis.https)}",
                    f"- Title: {analysis.title or 'missing'}",
                    f"- Meta description: {_format_bool(analysis.meta_description_present)}",
                    f"- Mobile viewport: {_format_bool(analysis.mobile_viewport_present)}",
                    f"- Contact signals: {', '.join(analysis.contact_signals) if analysis.contact_signals else 'missing'}",
                ]
            )
        lines.append(
            f"- Evidence-backed reasons: {'; '.join(lead.scores.reasons) if lead.scores.reasons else 'none'}"
        )
        lines.append(f"- Evidence items: {len(lead.evidence)}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_markdown_report(leads: list[CompanyLead], output_path, *, top: int = 50) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_markdown_report(leads, top=top), encoding="utf-8")


def _format_bool(value: bool | None) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unknown"
