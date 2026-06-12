from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlacePreset:
    name: str
    municipality: str
    district: str | None
    bbox: tuple[float, float, float, float]
    aliases: tuple[str, ...] = ()


class PlaceNotFoundError(ValueError):
    pass


PLACE_PRESETS: tuple[PlacePreset, ...] = (
    PlacePreset(
        name="porto",
        municipality="Porto",
        district="Porto",
        bbox=(-8.69, 41.12, -8.55, 41.19),
        aliases=("oporto", "porto-centro"),
    ),
    PlacePreset(
        name="lisboa",
        municipality="Lisboa",
        district="Lisboa",
        bbox=(-9.23, 38.68, -9.09, 38.8),
        aliases=("lisbon", "lisboa-centro"),
    ),
    PlacePreset(
        name="braga",
        municipality="Braga",
        district="Braga",
        bbox=(-8.46, 41.53, -8.39, 41.57),
        aliases=("braga-centro",),
    ),
    PlacePreset(
        name="coimbra",
        municipality="Coimbra",
        district="Coimbra",
        bbox=(-8.48, 40.17, -8.37, 40.24),
        aliases=("coimbra-centro",),
    ),
    PlacePreset(
        name="faro",
        municipality="Faro",
        district="Faro",
        bbox=(-7.98, 37.0, -7.87, 37.06),
        aliases=("faro-centro",),
    ),
)


def list_place_names() -> list[str]:
    return sorted(preset.name for preset in PLACE_PRESETS)


def resolve_place(value: str) -> PlacePreset:
    normalized = _normalize_place(value)
    for preset in PLACE_PRESETS:
        names = {preset.name, *preset.aliases}
        if normalized in {_normalize_place(name) for name in names}:
            return preset
    available = ", ".join(list_place_names())
    raise PlaceNotFoundError(f"Unknown place preset: {value}. Available presets: {available}")


def resolve_place_bbox(value: str) -> tuple[float, float, float, float]:
    return resolve_place(value).bbox


def _normalize_place(value: str) -> str:
    return value.strip().lower().replace(" ", "-").replace("_", "-")
