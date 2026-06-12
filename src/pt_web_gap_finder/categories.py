from __future__ import annotations

BASE_CATEGORIES: tuple[str, ...] = (
    "restaurant",
    "cafe",
    "bar",
    "fast_food",
    "dentist",
    "pharmacy",
    "clinic",
    "hairdresser",
    "real_estate",
    "gym",
    "bakery",
    "car_repair",
)

CATEGORY_BUNDLES: dict[str, list[str]] = {
    "restaurants": ["restaurant", "cafe", "bar", "fast_food"],
    "food-drink": ["restaurant", "cafe", "bar", "fast_food", "bakery"],
    "health": ["dentist", "pharmacy", "clinic"],
    "local-services": ["hairdresser", "real_estate", "gym", "bakery", "car_repair"],
}


class CategoryNotFoundError(ValueError):
    pass


def list_category_names() -> list[str]:
    return sorted({*BASE_CATEGORIES, *CATEGORY_BUNDLES})


def resolve_categories(value: str) -> list[str]:
    normalized = _normalize_category(value)
    if normalized in CATEGORY_BUNDLES:
        return CATEGORY_BUNDLES[normalized]
    if normalized in BASE_CATEGORIES:
        return [normalized]
    available = ", ".join(list_category_names())
    raise CategoryNotFoundError(
        f"Unknown category or bundle: {value}. Available categories and bundles: {available}"
    )


def _normalize_category(value: str) -> str:
    return value.strip().lower().replace(" ", "-").replace("_", "-")
