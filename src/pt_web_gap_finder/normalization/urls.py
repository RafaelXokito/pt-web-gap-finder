from __future__ import annotations


def normalize_url(value: str | None) -> str | None:
    if not value:
        return None
    url = value.strip()
    if not url:
        return None
    if url.startswith("//"):
        return "https:" + url
    if "://" not in url:
        return "https://" + url
    return url
