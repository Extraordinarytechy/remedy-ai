from __future__ import annotations
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

# Upper bounds on free text. They keep prompts, PDFs and payloads small on a public API.
SHORT_TEXT = 200
LONG_TEXT = 2000

UkRegion = Literal["england_wales", "northern_ireland", "scotland"]


class ReceiptData(BaseModel):
    store_name: Optional[str] = Field(default=None, max_length=SHORT_TEXT)
    purchase_date: Optional[str] = Field(default=None, max_length=40)
    item_description: Optional[str] = Field(default=None, max_length=LONG_TEXT)
    total_amount: Optional[float] = None
    # ISO currency for display. Not evidence: use currency_evidence for checks.
    currency: Optional[str] = Field(default=None, max_length=8)
    # The currency symbol or code actually read from the receipt (e.g. "$", "£", "GBP").
    # None when nothing was read. Only this field is used to cross-check the country.
    currency_evidence: Optional[str] = Field(default=None, max_length=8)
    payment_type: Optional[str] = Field(default=None, max_length=SHORT_TEXT)
    # Amazon Textract's own mean field confidence (0-1). None for sample or manual data.
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    source: Literal["textract", "sample", "unavailable"] = "sample"
    raw_fields: Dict[str, Any] = Field(default_factory=dict, max_length=60)


class VisualDefectEvidence(BaseModel):
    anomaly_detected: bool = False
    visible_physical_damage: bool = False
    physical_damage_severity: Literal["none", "cosmetic", "screen_cracked", "severe"] = "none"
    symptom_category: Optional[str] = Field(default=None, max_length=80)
    visual_observations: List[str] = Field(default_factory=list, max_length=20)
    # Where these observations came from: "bedrock", "sample" (demo fixture) or "unavailable".
    source: Literal["bedrock", "sample", "unavailable"] = "sample"
    disclaimer: str = (
        "Visual defect evidence analysis documents visible physical anomalies and reported symptoms; "
        "it explicitly abstains from internal electrical or root-cause engineering diagnosis."
    )


class NormalizedCase(BaseModel):
    case_id: str = Field(max_length=80)
    product_name: str = Field(min_length=1, max_length=SHORT_TEXT)
    product_brand: Optional[str] = Field(default=None, max_length=SHORT_TEXT)
    product_model: Optional[str] = Field(default=None, max_length=SHORT_TEXT)
    purchase_date: str = Field(max_length=40)  # YYYY-MM-DD
    failure_date: str = Field(max_length=40)   # YYYY-MM-DD
    purchase_country: str = Field(default="US", max_length=8)  # ISO country code (e.g. US, GB)
    # Only for purchase_country GB: the limitation period differs in Scotland.
    uk_region: Optional[UkRegion] = None
    retailer: Optional[str] = Field(default=None, max_length=SHORT_TEXT)
    payment_method: Optional[str] = Field(default=None, max_length=SHORT_TEXT)
    original_warranty_years: float = Field(default=1.0, ge=0, le=10)
    defect_description: str = Field(min_length=1, max_length=LONG_TEXT)
    # Date the claim would be made (YYYY-MM-DD). Defaults to today (UTC) when omitted.
    # Service-program and limitation windows are measured against this date.
    evaluation_date: Optional[str] = Field(default=None, max_length=40)
    already_paid_for_repair: bool = False
    # Check ids the user has explicitly confirmed (e.g. "country_currency").
    confirmed_checks: List[str] = Field(default_factory=list, max_length=10)
    receipt_data: Optional[ReceiptData] = None
    visual_evidence: Optional[VisualDefectEvidence] = None


class CaseCheck(BaseModel):
    """A consistency check between what the user typed and what their receipt shows."""
    id: str
    # hard: blocks the claim PDF until confirmed. soft: shown and printed, never blocks.
    severity: Literal["hard", "soft"]
    message: str
    confirm_label: Optional[str] = None
    confirmed: bool = False


class CaseTimeline(BaseModel):
    purchase_date: str
    failure_date: str
    claim_date: str
    months_before_failure: float


class ProvenanceChain(BaseModel):
    claim: str
    why_matched: str
    evidence: List[str]
    source_citation: str
    source_url: str
    conditions: List[str]
    exceptions: List[str]


class MatchedRoute(BaseModel):
    route_id: str
    route_type: Literal["manufacturer_service_program", "card_benefit", "statutory_consumer_law"]
    title: str
    provider: str
    status: Literal[
        "POTENTIALLY_ELIGIBLE",
        "ELIGIBLE_PENDING_INSPECTION",
        "PENDING_SERIAL_VERIFICATION",
        "NEEDS_REVERIFICATION",
        "NEEDS_CONFIRMATION",
        "OUTSIDE_WINDOW",
        "INSUFFICIENT_EVIDENCE",
    ]
    summary: str
    primary_source: Dict[str, str]
    provenance: ProvenanceChain
    recommended_action: str
    # The date this option closes, what that date is, and days left as of the claim date.
    deadline: Optional[str] = None
    deadline_label: Optional[str] = None
    days_left: Optional[int] = None
    related_sources: List[Dict[str, str]] = Field(default_factory=list)
    # Result of the latest automated Source Watch check for this route's source, if available.
    source_check: Optional[Dict[str, Any]] = None


class RemedyEvaluation(BaseModel):
    case_id: str
    evaluated_at: str
    evaluation_date: Optional[str] = None  # the "as of" date windows were measured against
    has_coverage: bool
    matched_routes: List[MatchedRoute] = Field(default_factory=list)
    unmatched_reason: Optional[str] = None
    # Sources that almost matched (e.g. program window already closed); never counted as coverage.
    notes: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)
    timeline: Optional[CaseTimeline] = None
    checks: List[CaseCheck] = Field(default_factory=list)
    # False while any hard check is unconfirmed; the server refuses to build a claim PDF.
    pdf_allowed: bool = True
    disclaimer: str = (
        "RemedyAI is a consumer claim-preparation tool and does not provide legal advice or guarantee "
        "coverage or refunds. Determinations are based on documented primary source policies and submitted evidence. "
        "Final resolution rests with the respective manufacturer, issuing bank, or retailer."
    )
