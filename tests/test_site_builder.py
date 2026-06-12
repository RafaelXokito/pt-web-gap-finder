import json

from pt_web_gap_finder.models import Address, CompanyLead, Contacts, LeadScores, OnlinePresence
from pt_web_gap_finder.site_builder import (
    build_ship_ready_site_package,
    build_site_package,
    select_site_lead,
)


def sample_lead() -> CompanyLead:
    lead = CompanyLead(
        id="osm:node:42",
        name="Barbearia Sousa",
        category="hairdresser",
        address=Address(locality="Porto", municipality="Porto", district="Porto"),
        contacts=Contacts(phone="+351 912 000 000", email="ola@barbeariasousa.pt"),
        online_presence=OnlinePresence(website_found=False),
    )
    lead.scores = LeadScores(opportunity_score=45, confidence_score=60, priority="low")
    return lead


def test_select_site_lead_prefers_explicit_id():
    leads = [sample_lead(), sample_lead().model_copy(update={"id": "osm:node:99", "name": "Outro Negócio"})]

    selected = select_site_lead(leads, lead_id="osm:node:99")

    assert selected.id == "osm:node:99"
    assert selected.name == "Outro Negócio"


def test_slugify_normalizes_accents_for_stable_output_paths():
    from pt_web_gap_finder.site_builder import slugify

    assert slugify("Bump - Chaves, Comandos e Soluções de Segurança, Lda.") == (
        "bump-chaves-comandos-e-solucoes-de-seguranca-lda"
    )


def test_build_site_package_writes_grounded_site_artifacts(tmp_path):
    output_dir = tmp_path / "barbearia-site"

    written = build_site_package(sample_lead(), output_dir)

    names = {path.name for path in written}
    assert names == {
        "brief.md",
        "content.json",
        "index.html",
        "styles.css",
        "hermes-redesign-prompt.md",
    }
    content = json.loads((output_dir / "content.json").read_text(encoding="utf-8"))
    assert content["company_name"] == "Barbearia Sousa"
    assert content["locality"] == "Porto"
    assert content["contacts"]["phone"] == "+351 912 000 000"
    html = (output_dir / "index.html").read_text(encoding="utf-8")
    assert "Barbearia Sousa" in html
    assert "Porto" in html
    assert "+351 912 000 000" in html
    brief = (output_dir / "brief.md").read_text(encoding="utf-8")
    assert "evidence-backed website starter" in brief
    assert "Confirm before publishing" in brief
    prompt = (output_dir / "hermes-redesign-prompt.md").read_text(encoding="utf-8")
    assert "design-taste-frontend" in prompt
    assert "gpt-taste" in prompt
    assert "image-to-code" in prompt


def test_build_ship_ready_site_package_writes_full_handoff_bundle(tmp_path):
    output_dir = tmp_path / "ship-ready-site"

    written = build_ship_ready_site_package(sample_lead(), output_dir)

    names = {path.name for path in written}
    assert names == {
        "brief.md",
        "content.json",
        "index.html",
        "styles.css",
        "hermes-redesign-prompt.md",
        "design-plan.md",
        "design-analysis.md",
        "ship-checklist.md",
        "publish-ready-summary.md",
    }
    design_plan = (output_dir / "design-plan.md").read_text(encoding="utf-8")
    assert "<design_plan>" in design_plan
    assert "AIDA Check" in design_plan
    assert "design-taste-frontend" in design_plan
    analysis = (output_dir / "design-analysis.md").read_text(encoding="utf-8")
    assert "Section 1" in analysis
    assert "Section 6" in analysis
    checklist = (output_dir / "ship-checklist.md").read_text(encoding="utf-8")
    assert "Pre-flight" in checklist
    summary = (output_dir / "publish-ready-summary.md").read_text(encoding="utf-8")
    assert "Ready to ship after human confirmation" in summary


def test_ship_ready_package_avoids_broken_contact_links_when_details_are_missing(tmp_path):
    lead = sample_lead().model_copy(update={"contacts": Contacts()})
    output_dir = tmp_path / "ship-ready-missing-contacts"

    build_ship_ready_site_package(lead, output_dir)

    html = (output_dir / "index.html").read_text(encoding="utf-8")
    assert 'href="tel:Confirm phone number"' not in html
    assert 'href="mailto:Confirm email address"' not in html
    assert 'href="#confirm"' in html
