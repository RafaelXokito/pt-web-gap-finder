from __future__ import annotations

from pydantic import BaseModel


class Settings(BaseModel):
    overpass_url: str = "https://overpass-api.de/api/interpreter"
    user_agent: str = "pt-web-gap-finder/0.1 (+https://github.com/RafaelXokito/pt-web-gap-finder)"
    request_timeout_seconds: float = 30.0
    max_concurrency: int = 5
