from __future__ import annotations
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class ReceiptData(BaseModel):
    store_name: Optional[str] = None
    purchase_date: Optional[str] = None
    item_description: Optional[str] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = "USD"
    payment_type: Optional[str] = None
    # Amazon Textract's own mean field confidence (0-1). None for sample or manual data.
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    source: Literal["textract", "sample", "unavailable"] = "sample"
    raw_fields: Dict[str, Any] = Field(default_factory=dict)


class VisualDefectEvidence(BaseModel):
    anomaly_detected: bool = False
    visible_physical_damage: bool = False
    physical_damage_severity: Literal["none", "cosmetic", "screen_cracked", "severe"] = "none"
    symptom_category: Optional[str] = None
    visual_observations: List[str] = Field(default_factory=list)
    # Where these observations came from: "bedrock", "sample" (demo fixture) or "unavailable".
    source: Literal["bedrock", "sample", "unavailable"] = "sample"
    disclaimer: str = (
        "Visual defect evidence analysis documents visible physical anomalies and reported symptoms; "
        "it explicitly abstains from internal electrical or root-cause engineering diagnosis."
    )


class NormalizedCase(BaseModel):
    case_id: str
    product_name: str
    product_brand: Optional[str] = None
    product_model: Optional[str] = None
    purchase_date: str  # YYYY-MM-DD
    failure_date: str   # YYYY-MM-DD
    purchase_country: str = "US"  # ISO country code (e.g. US, GB)
    retailer: Optional[str] = None
    payment_method: Optional[str] = None
    original_warranty_years: float = 1.0
    defect_description: str
    # Date the claim would be made (YYYY-MM-DD). Defaults to today (UTC) when omitted.
    # Service-program and limitation windows are measured against this date.
    evaluation_date: Optional[str] = None
    already_paid_for_repair: bool = False
    receipt_data: Optional[ReceiptData] = None
    visual_evidence: Optional[VisualDefectEvidence] = None


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
        "OUTSIDE_WINDOW",
        "INSUFFICIENT_EVIDENCE",
    ]
    summary: str
    primary_source: Dict[str, str]
    provenance: ProvenanceChain
    recommended_action: str
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
    disclaimer: str = (
        "RemedyAI is a consumer claim-preparation tool and does not provide legal advice or guarantee "
        "coverage or refunds. Determinations are based on documented primary source policies and submitted evidence. "
        "Final resolution rests with the respective manufacturer, issuing bank, or retailer."
    )
