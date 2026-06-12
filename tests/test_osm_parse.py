from pt_web_gap_finder.models import Confidence
from pt_web_gap_finder.sources.osm import parse_osm_element


def test_parse_osm_node_to_company_lead_with_contacts_and_website():
    element = {
        "type": "node",
        "id": 123,
        "lat": 41.1496,
        "lon": -8.6109,
        "tags": {
            "name": "Restaurante Exemplo",
            "amenity": "restaurant",
            "addr:city": "Porto",
            "addr:postcode": "4000-000",
            "phone": "+351 222 000 000",
            "email": "info@example.pt",
            "website": "www.example.pt",
        },
    }

    lead = parse_osm_element(element, category="restaurant")

    assert lead.id == "osm:node:123"
    assert lead.name == "Restaurante Exemplo"
    assert lead.category == "restaurant"
    assert lead.address.lat == 41.1496
    assert lead.address.lon == -8.6109
    assert lead.address.locality == "Porto"
    assert lead.contacts.phone == "+351 222 000 000"
    assert lead.contacts.email == "info@example.pt"
    assert lead.online_presence.website_found is True
    assert lead.online_presence.website_url == "https://www.example.pt"
    assert any(item.field == "website" for item in lead.evidence)


def test_parse_osm_way_uses_center_and_marks_missing_website():
    element = {
        "type": "way",
        "id": 456,
        "center": {"lat": 41.15, "lon": -8.61},
        "tags": {
            "name": "Café Sem Site",
            "amenity": "cafe",
            "contact:facebook": "https://facebook.com/cafesemsite",
        },
    }

    lead = parse_osm_element(element, category="cafe")

    assert lead.id == "osm:way:456"
    assert lead.address.lat == 41.15
    assert lead.address.lon == -8.61
    assert lead.online_presence.website_found is False
    assert lead.online_presence.social_only is True
    assert lead.contacts.social_profiles["facebook"] == "https://facebook.com/cafesemsite"
    missing_website = [item for item in lead.evidence if item.field == "website"]
    assert missing_website[0].confidence == Confidence.MEDIUM
