from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import base64
from datetime import datetime, timezone

from src.models.schemas import NormalizedCase, RemedyEvaluation
from src.engine.eligibility import EligibilityEngine
from src.services.textract_service import TextractService
from src.services.bedrock_service import BedrockVisionService
from src.services.pdf_service import ClaimPdfService
from src.services import source_watch, usage_guard
from src.fixtures import DEMO_FIXTURES

MAX_IMAGE_BYTES = 4 * 1024 * 1024  # after base64 decoding; the frontend downsizes photos first

app = FastAPI(
    title="RemedyAI API",
    description="Evidence-Grounded Consumer Claim Preparation Engine",
    version="1.1.0",
)

# Public, unauthenticated API: no cookies or credentials are used.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

engine = EligibilityEngine()
textract_service = TextractService()
bedrock_service = BedrockVisionService()
pdf_service = ClaimPdfService()


class IntakeRequest(BaseModel):
    case_id: Optional[str] = None
    product_name: str
    product_brand: Optional[str] = None
    product_model: Optional[str] = None
    purchase_date: str
    failure_date: str
    purchase_country: str = "US"
    retailer: Optional[str] = None
    payment_method: Optional[str] = None
    original_warranty_years: float = 1.0
    defect_description: str
    evaluation_date: Optional[str] = None
    already_paid_for_repair: bool = False
    receipt_base64: Optional[str] = None
    defect_image_base64: Optional[str] = None


class ExtractRequest(BaseModel):
    receipt_base64: Optional[str] = None
    defect_image_base64: Optional[str] = None
    product_hint: Optional[str] = None


class GeneratePackageRequest(BaseModel):
    case: NormalizedCase
    evaluation: RemedyEvaluation


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "RemedyAI",
        "version": "1.1.0",
        "policy": "Closed-World Evidence Policy",
        "knowledge_records": sorted(engine.records.keys()),
    }


@app.get("/api/fixtures")
def get_fixtures():
    """Returns the predefined one-click demo fixtures (sample data) for testing and evaluation."""
    return DEMO_FIXTURES


@app.get("/api/sources")
def get_sources():
    """Every primary source in the corpus, with the latest automated Source Watch result."""
    status = source_watch.load_status()
    sources = []
    for rid, rec in sorted(engine.records.items()):
        sources.append({
            "id": rid,
            "program_name": rec.get("program_name"),
            "issuer": rec.get("issuer_or_brand"),
            "source_url": rec.get("source_url"),
            "human_verified_at": rec.get("verified_at"),
            "watch": {k: v for k, v in status.get(rid, {}).items() if not k.startswith("_") and k != "content_hash"},
        })
    return {"sources": sources, "apple_index": status.get("apple_index")}


def _decode_image(b64: str, label: str) -> bytes:
    if "," in b64[:100]:  # tolerate data URLs
        b64 = b64.split(",", 1)[1]
    try:
        data = base64.b64decode(b64, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail=f"{label} is not valid base64.")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail=f"{label} is larger than 4 MB.")
    return data


@app.post("/api/intake", response_model=NormalizedCase)
def process_intake(request: IntakeRequest):
    """
    Intake pipeline: parses receipt and defect imagery via Amazon Textract and Amazon Bedrock
    to assemble a NormalizedCase. When no image is supplied, no visual evidence is recorded.
    """
    case_id = request.case_id or f"case_{int(datetime.now(timezone.utc).timestamp())}"

    receipt_bytes = _decode_image(request.receipt_base64, "Receipt image") if request.receipt_base64 else None
    defect_bytes = _decode_image(request.defect_image_base64, "Defect photo") if request.defect_image_base64 else None

    # Public, unauthenticated endpoint: paid AI calls are capped per day (fails closed).
    try:
        usage_guard.consume(int(receipt_bytes is not None) + int(defect_bytes is not None))
    except usage_guard.LimitReached as e:
        raise HTTPException(status_code=429, detail=str(e))

    receipt_data = textract_service.analyze_receipt_bytes(receipt_bytes) if receipt_bytes else None
    visual_evidence = (
        bedrock_service.analyze_defect_image(defect_bytes, product_hint=request.product_name)
        if defect_bytes
        else None
    )

    return NormalizedCase(
        case_id=case_id,
        product_name=request.product_name,
        product_brand=request.product_brand,
        product_model=request.product_model,
        purchase_date=request.purchase_date,
        failure_date=request.failure_date,
        purchase_country=request.purchase_country,
        retailer=request.retailer,
        payment_method=request.payment_method,
        original_warranty_years=request.original_warranty_years,
        defect_description=request.defect_description,
        evaluation_date=request.evaluation_date,
        already_paid_for_repair=request.already_paid_for_repair,
        receipt_data=receipt_data,
        visual_evidence=visual_evidence,
    )


@app.post("/api/extract")
def extract_evidence(req: ExtractRequest):
    """
    Reads a receipt photo with Amazon Textract (AnalyzeExpense) and a defect photo with
    Amazon Bedrock. The user reviews and corrects the result before anything is evaluated.
    """
    receipt_bytes = _decode_image(req.receipt_base64, "Receipt image") if req.receipt_base64 else None
    defect_bytes = _decode_image(req.defect_image_base64, "Defect photo") if req.defect_image_base64 else None
    if not receipt_bytes and not defect_bytes:
        raise HTTPException(status_code=400, detail="Attach a receipt photo, a defect photo, or both.")
    try:
        usage_guard.consume(int(receipt_bytes is not None) + int(defect_bytes is not None))
    except usage_guard.LimitReached as e:
        raise HTTPException(status_code=429, detail=str(e))
    return {
        "receipt_data": textract_service.analyze_receipt_bytes(receipt_bytes).model_dump() if receipt_bytes else None,
        "visual_evidence": bedrock_service.analyze_defect_image(defect_bytes, product_hint=req.product_hint).model_dump()
        if defect_bytes
        else None,
    }


@app.post("/api/evaluate", response_model=RemedyEvaluation)
def evaluate_coverage(case: NormalizedCase):
    """
    Evaluates submitted case evidence against the verified primary source corpus.
    Closed-world: returns NO VERIFIED COVERAGE FOUND if no source record matches.
    """
    return engine.evaluate(case, source_status=source_watch.load_status())


@app.post("/api/generate-package")
def generate_claim_package(req: GeneratePackageRequest):
    """Generates an evidence-grounded Claim Package PDF using ReportLab."""
    try:
        pdf_bytes = pdf_service.generate_pdf(req.case, req.evaluation)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=RemedyAI_Claim_{req.case.case_id}.pdf"
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {e}")
