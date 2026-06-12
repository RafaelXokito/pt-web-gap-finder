from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EvidenceItem(BaseModel):
    field: str
    value: Any = None
    source_name: str
    source_type: Literal["open_data", "official_registry", "search_api", "company_website", "derived"]
    source_url: str | None = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: Confidence = Confidence.MEDIUM
    notes: str | None = None


class Address(BaseModel):
    street: str | None = None
    postal_code: str | None = None
    locality: str | None = None
    municipality: str | None = None
    district: str | None = None
    lat: float | None = None
    lon: float | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class Contacts(BaseModel):
    phone: str | None = None
    mobile: str | None = None
    email: str | None = None
    contact_url: str | None = None
    social_profiles: dict[str, str] = Field(default_factory=dict)


class OnlinePresence(BaseModel):
    website_found: bool | None = None
    website_url: str | None = None
    website_discovery_method: str | None = None
    domain_confidence: float = 0.0
    social_only: bool = False
    search_candidates: list[str] = Field(default_factory=list)


class WebsiteAnalysis(BaseModel):
    http_status: int | None = None
    final_url: str | None = None
    https: bool | None = None
    reachable: bool | None = None
    redirect_chain: list[str] = Field(default_factory=list)
    title: str | None = None
    meta_description_present: bool | None = None
    mobile_viewport_present: bool | None = None
    contact_signals: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class LeadScores(BaseModel):
    opportunity_score: int = 0
    confidence_score: int = 0
    priority: Literal["hot", "warm", "low", "ignore"] = "ignore"
    reasons: list[str] = Field(default_factory=list)


class CompanyLead(BaseModel):
    id: str
    name: str
    normalized_name: str | None = None
    country: str = "PT"
    sector: str | None = None
    category: str | None = None
    legal_name: str | None = None
    tax_id: str | None = None
    source_ids: list[str] = Field(default_factory=list)
    address: Address | None = None
    contacts: Contacts = Field(default_factory=Contacts)
    online_presence: OnlinePresence = Field(default_factory=OnlinePresence)
    website_analysis: WebsiteAnalysis | None = None
    scores: LeadScores = Field(default_factory=LeadScores)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
