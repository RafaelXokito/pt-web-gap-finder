from pt_web_gap_finder.models import CompanyLead, LeadScores, OnlinePresence, WebsiteAnalysis
from pt_web_gap_finder.report import classify_gap, render_markdown_report


def lead(
    name: str,
    score: int,
    priority: str,
    *,
    website_found: bool | None = None,
    website_url: str | None = None,
    analysis: WebsiteAnalysis | None = None,
    reasons: list[str] | None = None,
) -> CompanyLead:
    return CompanyLead(
        id=f"lead:{name}",
        name=name,
        category="restaurant",
        online_presence=OnlinePresence(website_found=website_found, website_url=website_url),
        website_analysis=analysis,
        scores=LeadScores(
            opportunity_score=score,
            confidence_score=75,
            priority=priority,  # type: ignore[arg-type]
            reasons=reasons or [],
        ),
    )


def test_classify_gap_names_core_sales_opportunities():
    assert classify_gap(lead("Sem Site", 45, "low", website_found=False)) == "No website found"
    assert (
        classify_gap(
            lead(
                "Site Quebrado",
                55,
                "warm",
                website_found=True,
                website_url="https://broken.example",
                analysis=WebsiteAnalysis(reachable=False),
            )
        )
        == "Broken or unreachable website"
    )
    assert (
        classify_gap(
            lead(
                "Site Fraco",
                35,
                "low",
                website_found=True,
                website_url="http://weak.example",
                analysis=WebsiteAnalysis(
                    reachable=True,
                    https=False,
                    meta_description_present=False,
                    mobile_viewport_present=False,
                    contact_signals=[],
                ),
            )
        )
        == "Weak website"
    )
    assert (
        classify_gap(
            lead(
                "Browser Check",
                0,
                "ignore",
                website_found=True,
                website_url="https://browser-check.example",
                analysis=WebsiteAnalysis(
                    http_status=403,
                    reachable=None,
                    notes=["Browser/bot-protection challenge detected"],
                ),
            )
        )
        == "Manual verification required"
    )


def test_render_markdown_report_sorts_top_opportunities_and_includes_pitch_angles():
    leads = [
        lead("Good Site", 0, "ignore", website_found=True, website_url="https://good.example"),
        lead("Sem Site", 45, "low", website_found=False, reasons=["No website found in available evidence"]),
        lead(
            "Site Quebrado",
            80,
            "hot",
            website_found=True,
            website_url="https://broken.example",
            analysis=WebsiteAnalysis(reachable=False, notes=["timed out"]),
            reasons=["Website is unreachable"],
        ),
    ]

    report = render_markdown_report(leads, top=2)

    assert report.startswith("# Portugal Website Gap Finder Report")
    assert "## Summary" in report
    assert "Total leads analyzed: 3" in report
    assert "Hot: 1" in report
    assert report.index("Site Quebrado") < report.index("Sem Site")
    assert "Gap type: Broken or unreachable website" in report
    assert "Pitch angle: Repair trust-critical web presence" in report
    assert "Evidence-backed reasons: Website is unreachable" in report
    assert "Good Site" not in report
