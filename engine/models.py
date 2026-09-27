"""Data models for Vera AI Engagement Engine."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal


@dataclass
class VoiceProfile:
    tone: str = "professional"
    register: str = "collegial"
    code_mix: str = "english"
    vocab_allowed: List[str] = field(default_factory=list)
    vocab_taboo: List[str] = field(default_factory=list)
    salutation_examples: List[str] = field(default_factory=list)
    tone_examples: List[str] = field(default_factory=list)


@dataclass
class OfferTemplate:
    id: str
    title: str
    value: str
    audience: str
    type: str


@dataclass
class PeerStats:
    scope: str = ""
    avg_rating: float = 4.0
    avg_review_count: int = 50
    avg_views_30d: int = 1500
    avg_calls_30d: int = 10
    avg_directions_30d: int = 25
    avg_ctr: float = 0.025
    avg_photos: int = 5
    avg_post_freq_days: int = 14
    retention_6mo_pct: float = 0.35


@dataclass
class CategoryContext:
    slug: str
    display_name: str = ""
    voice: VoiceProfile = field(default_factory=VoiceProfile)
    offer_catalog: List[Dict[str, Any]] = field(default_factory=list)
    peer_stats: PeerStats = field(default_factory=PeerStats)
    digest: List[Dict[str, Any]] = field(default_factory=list)
    patient_content_library: List[Dict[str, Any]] = field(default_factory=list)
    seasonal_beats: List[Dict[str, Any]] = field(default_factory=list)
    trend_signals: List[Dict[str, Any]] = field(default_factory=list)
    raw_payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Identity:
    name: str = ""
    city: str = ""
    locality: str = ""
    place_id: str = ""
    verified: bool = False
    languages: List[str] = field(default_factory=lambda: ["en"])
    owner_first_name: str = ""
    established_year: Optional[int] = None


@dataclass
class PerformanceSnapshot:
    window_days: int = 30
    views: int = 0
    calls: int = 0
    directions: int = 0
    ctr: float = 0.0
    leads: int = 0
    delta_7d: Dict[str, float] = field(default_factory=dict)


@dataclass
class MerchantContext:
    merchant_id: str
    category_slug: str
    identity: Identity = field(default_factory=Identity)
    subscription: Dict[str, Any] = field(default_factory=dict)
    performance: PerformanceSnapshot = field(default_factory=PerformanceSnapshot)
    offers: List[Dict[str, Any]] = field(default_factory=list)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    customer_aggregate: Dict[str, Any] = field(default_factory=dict)
    signals: List[str] = field(default_factory=list)
    review_themes: List[Dict[str, Any]] = field(default_factory=list)
    raw_payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TriggerContext:
    id: str
    scope: Literal["merchant", "customer"]
    kind: str
    source: Literal["external", "internal"]
    merchant_id: str
    customer_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    urgency: int = 1
    suppression_key: str = ""
    expires_at: Optional[str] = None
    raw_payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CustomerContext:
    customer_id: str
    merchant_id: str
    identity: Dict[str, Any] = field(default_factory=dict)
    relationship: Dict[str, Any] = field(default_factory=dict)
    state: str = "active"
    preferences: Dict[str, Any] = field(default_factory=dict)
    consent: Dict[str, Any] = field(default_factory=dict)
    raw_payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComposedMessage:
    body: str
    cta: str  # "binary" | "open_ended" | "none"
    send_as: str  # "vera" | "merchant"
    suppression_key: str
    rationale: str
    template_name: Optional[str] = None
    template_params: List[str] = field(default_factory=list)
    conversation_id: Optional[str] = None
    trigger_id: Optional[str] = None
    merchant_id: Optional[str] = None
    customer_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "body": self.body,
            "cta": self.cta,
            "send_as": self.send_as,
            "suppression_key": self.suppression_key,
            "rationale": self.rationale,
        }
        if self.conversation_id:
            d["conversation_id"] = self.conversation_id
        if self.merchant_id:
            d["merchant_id"] = self.merchant_id
        if self.customer_id is not None:
            d["customer_id"] = self.customer_id
        if self.trigger_id:
            d["trigger_id"] = self.trigger_id
        if self.template_name:
            d["template_name"] = self.template_name
        if self.template_params:
            d["template_params"] = self.template_params
        return d
