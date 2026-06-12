import asyncio

from pt_web_gap_finder.models import CompanyLead, OnlinePresence
from pt_web_gap_finder.site_analysis import StaticHTTPClient, analyze_lead_site, run_site_analysis


def test_analyze_lead_site_extracts_quality_signals_and_evidence():
    lead = CompanyLead(
        id="osm:node:1",
        name="Clínica Exemplo",
        online_presence=OnlinePresence(
            website_found=True,
            website_url="clinica.example",
            website_discovery_method="osm:website",
        ),
    )
    html = """
    <html>
      <head>
        <title>Clínica Exemplo Porto</title>
        <meta name="description" content="Dentista no Porto">
        <meta name="viewport" content="width=device-width, initial-scale=1">
      </head>
      <body>
        <a href="/contactos">Contactos</a>
        <a href="tel:+351222000000">Telefone</a>
        <a href="mailto:geral@clinica.example">Email</a>
      </body>
    </html>
    """
    client = StaticHTTPClient(
        {
            "https://clinica.example": {
                "status_code": 200,
                "url": "https://clinica.example/",
                "history": ["http://clinica.example"],
                "text": html,
            }
        }
    )

    analyzed = asyncio.run(analyze_lead_site(lead, client=client, timeout=3.0))

    assert analyzed.website_analysis is not None
    assert analyzed.website_analysis.reachable is True
    assert analyzed.website_analysis.http_status == 200
    assert analyzed.website_analysis.final_url == "https://clinica.example/"
    assert analyzed.website_analysis.https is True
    assert analyzed.website_analysis.redirect_chain == ["http://clinica.example"]
    assert analyzed.website_analysis.title == "Clínica Exemplo Porto"
    assert analyzed.website_analysis.meta_description_present is True
    assert analyzed.website_analysis.mobile_viewport_present is True
    assert analyzed.website_analysis.contact_signals == ["contact_page", "email", "phone"]
    assert analyzed.scores.opportunity_score == 0
    assert any(item.field == "website_analysis.title" for item in analyzed.evidence)


def test_analyze_lead_site_marks_unreachable_site_as_warm_opportunity():
    lead = CompanyLead(
        id="osm:node:2",
        name="Loja Exemplo",
        online_presence=OnlinePresence(website_found=True, website_url="https://loja.example"),
    )
    client = StaticHTTPClient({"https://loja.example": TimeoutError("timed out")})

    analyzed = asyncio.run(analyze_lead_site(lead, client=client, timeout=0.1))

    assert analyzed.website_analysis is not None
    assert analyzed.website_analysis.reachable is False
    assert "timed out" in analyzed.website_analysis.notes[0]
    assert analyzed.scores.priority == "warm"
    assert "Website is unreachable" in analyzed.scores.reasons


def test_run_site_analysis_skips_leads_without_websites():
    without_website = CompanyLead(
        id="osm:node:3",
        name="Café Sem Site",
        online_presence=OnlinePresence(website_found=False),
    )

    analyzed = asyncio.run(run_site_analysis([without_website], client=StaticHTTPClient({})))

    assert analyzed[0].website_analysis is None
    assert analyzed[0].scores.opportunity_score == 45
    assert analyzed[0].scores.priority == "low"
