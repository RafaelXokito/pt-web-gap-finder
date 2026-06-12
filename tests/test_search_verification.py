import asyncio

from pt_web_gap_finder.models import CompanyLead, OnlinePresence
from pt_web_gap_finder.search_verification import (
    SearchResult,
    StaticSearchClient,
    build_search_query,
    verify_lead_website,
)


def test_verify_lead_website_sets_official_website_from_search_result():
    lead = CompanyLead(
        id="osm:node:1",
        name="Barbearia Sousa",
        category="hairdresser",
        online_presence=OnlinePresence(website_found=False),
    )
    query = build_search_query(lead)
    client = StaticSearchClient(
        {
            query: [
                SearchResult(
                    url="https://www.facebook.com/barbeariasousa",
                    title="Barbearia Sousa | Facebook",
                    snippet="Página oficial no Facebook",
                ),
                SearchResult(
                    url="https://barbeariasousa.pt",
                    title="Barbearia Sousa - Porto",
                    snippet="Cortes masculinos e marcações no Porto.",
                ),
            ]
        }
    )

    verified = asyncio.run(verify_lead_website(lead, client=client, limit=5))

    assert verified.online_presence.website_found is True
    assert verified.online_presence.website_url == "https://barbeariasousa.pt"
    assert verified.online_presence.website_discovery_method == "bing_search"
    assert verified.online_presence.domain_confidence >= 0.6
    assert verified.online_presence.search_candidates == [
        "https://www.facebook.com/barbeariasousa",
        "https://barbeariasousa.pt",
    ]


def test_verify_lead_website_marks_social_only_when_search_finds_no_website():
    lead = CompanyLead(
        id="osm:node:2",
        name="Padaria Santo António",
        category="bakery",
        online_presence=OnlinePresence(website_found=False),
    )
    query = build_search_query(lead)
    client = StaticSearchClient(
        {
            query: [
                SearchResult(
                    url="https://www.instagram.com/padariasantoantonio/",
                    title="Padaria Santo António (@padariasantoantonio)",
                    snippet="Instagram oficial da padaria.",
                ),
                SearchResult(
                    url="https://www.facebook.com/padariasantoantonio",
                    title="Padaria Santo António | Facebook",
                    snippet="Padaria local.",
                ),
            ]
        }
    )

    verified = asyncio.run(verify_lead_website(lead, client=client, limit=5))

    assert verified.online_presence.website_found is False
    assert verified.online_presence.website_url is None
    assert verified.online_presence.social_only is True
    assert verified.online_presence.website_discovery_method == "search_social_only"
    assert verified.online_presence.search_candidates == [
        "https://www.instagram.com/padariasantoantonio/",
        "https://www.facebook.com/padariasantoantonio",
    ]


def test_verify_lead_website_rejects_directory_or_generic_false_positives():
    lead = CompanyLead(
        id="osm:node:3",
        name="Auto Reparadora Brites",
        category="car_repair",
        online_presence=OnlinePresence(website_found=False),
    )
    query = build_search_query(lead)
    client = StaticSearchClient(
        {
            query: [
                SearchResult(
                    url="https://www.auto.pt",
                    title="Auto.PT | Compra e Venda de Carros Usados",
                    snippet="Portal de classificados automóvel.",
                ),
                SearchResult(
                    url="https://guiaempresas.pt/barbearia/marinha-grande",
                    title="Barbearia em Marinha Grande - Guia Empresas",
                    snippet="Diretório de empresas.",
                ),
            ]
        }
    )

    verified = asyncio.run(verify_lead_website(lead, client=client, limit=5))

    assert verified.online_presence.website_found is False
    assert verified.online_presence.website_url is None
    assert verified.online_presence.website_discovery_method == "search_no_website_found"


def test_verify_lead_website_does_not_mark_unrelated_social_results_as_social_only():
    lead = CompanyLead(
        id="osm:node:4",
        name="Caulinos",
        category="bakery",
        online_presence=OnlinePresence(website_found=False),
    )
    query = build_search_query(lead)
    client = StaticSearchClient(
        {
            query: [
                SearchResult(
                    url="https://www.youtube.com/watch?v=123",
                    title="Top 10 baking videos",
                    snippet="Completely unrelated YouTube result.",
                ),
                SearchResult(
                    url="https://www.youtube.com/channel/abc",
                    title="Random cooking channel",
                    snippet="Another unrelated social result.",
                ),
            ]
        }
    )

    verified = asyncio.run(verify_lead_website(lead, client=client, limit=5))

    assert verified.online_presence.website_found is False
    assert verified.online_presence.social_only is False
    assert verified.online_presence.website_discovery_method == "search_no_website_found"
