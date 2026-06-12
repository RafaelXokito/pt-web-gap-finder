import pytest

from pt_web_gap_finder.places import PlaceNotFoundError, list_place_names, resolve_place_bbox


def test_resolve_place_bbox_accepts_common_portuguese_aliases():
    assert resolve_place_bbox("porto") == (-8.69, 41.12, -8.55, 41.19)
    assert resolve_place_bbox("Lisboa") == (-9.23, 38.68, -9.09, 38.8)
    assert resolve_place_bbox("braga-centro") == (-8.46, 41.53, -8.39, 41.57)


def test_resolve_place_bbox_raises_helpful_error_for_unknown_place():
    with pytest.raises(PlaceNotFoundError) as exc_info:
        resolve_place_bbox("atlantis")

    message = str(exc_info.value)
    assert "Unknown place preset: atlantis" in message
    assert "porto" in message
    assert "lisboa" in message


def test_list_place_names_is_sorted_and_contains_primary_presets():
    names = list_place_names()

    assert names == sorted(names)
    assert {"porto", "lisboa", "braga", "coimbra", "faro"}.issubset(names)
