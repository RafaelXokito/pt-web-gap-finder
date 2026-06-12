import pytest

from pt_web_gap_finder.categories import CategoryNotFoundError, list_category_names, resolve_categories


def test_resolve_categories_expands_campaign_bundles():
    assert resolve_categories("restaurants") == ["restaurant", "cafe", "bar", "fast_food"]
    assert resolve_categories("health") == ["dentist", "pharmacy", "clinic"]
    assert resolve_categories("local-services") == [
        "hairdresser",
        "real_estate",
        "gym",
        "bakery",
        "car_repair",
    ]


def test_resolve_categories_keeps_single_supported_category():
    assert resolve_categories("dentist") == ["dentist"]


def test_resolve_categories_raises_helpful_error_for_unknown_category():
    with pytest.raises(CategoryNotFoundError) as exc_info:
        resolve_categories("spaceships")

    message = str(exc_info.value)
    assert "Unknown category or bundle: spaceships" in message
    assert "restaurants" in message
    assert "health" in message


def test_list_category_names_includes_bundles_and_base_categories():
    names = list_category_names()

    assert names == sorted(names)
    assert {"restaurant", "restaurants", "health", "local-services"}.issubset(names)
