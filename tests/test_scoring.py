from pt_web_gap_finder.models import CompanyLead, OnlinePresence, WebsiteAnalysis
from pt_web_gap_finder.scoring.lead_score import score_lead


def test_no_website_lead_scores_hot_or_warm():
    lead = CompanyLead(
        id="x",
        name="Example Business",
        online_presence=OnlinePresence(website_found=False, social_only=True),
    )
    score = score_lead(lead)
    assert score.opportunity_score >= 75
    assert "No website" in " ".join(score.reasons)


def test_unreachable_non_https_site_adds_reasons():
    lead = CompanyLead(
        id="x",
        name="Example Business",
        online_presence=OnlinePresence(website_found=True, website_url="http://example.test"),
        website_analysis=WebsiteAnalysis(reachable=False, https=False, mobile_viewport_present=False),
    )
    score = score_lead(lead)
    assert score.opportunity_score >= 80
    assert any("unreachable" in reason for reason in score.reasons)
