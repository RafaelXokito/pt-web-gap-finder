from __future__ import annotations

from pt_web_gap_finder.models import CompanyLead, LeadScores


def score_lead(lead: CompanyLead) -> LeadScores:
    score = 0
    reasons: list[str] = []

    if lead.online_presence.website_found is False:
        score += 45
        reasons.append("No website found in available evidence")
    if lead.online_presence.social_only:
        score += 30
        reasons.append("Only social presence found")

    analysis = lead.website_analysis
    if analysis:
        if analysis.reachable is False:
            score += 40
            reasons.append("Website is unreachable")
        if analysis.https is False:
            score += 20
            reasons.append("Website does not use HTTPS")
        if analysis.mobile_viewport_present is False:
            score += 20
            reasons.append("No mobile viewport detected")
        if analysis.meta_description_present is False:
            score += 5
            reasons.append("No meta description detected")
        if not analysis.contact_signals:
            score += 10
            reasons.append("No contact signal detected on homepage")

    confidence = 50 + min(len(lead.evidence) * 5, 40)
    if not lead.name:
        confidence -= 30
    confidence = max(0, min(confidence, 100))
    score = max(0, min(score, 100))

    if score >= 80:
        priority = "hot"
    elif score >= 55:
        priority = "warm"
    elif score >= 25:
        priority = "low"
    else:
        priority = "ignore"

    return LeadScores(
        opportunity_score=score,
        confidence_score=confidence,
        priority=priority,
        reasons=reasons,
    )
