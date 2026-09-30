import base64
import hmac
import os
import re
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.models.schemas import NormalizedCase, RemedyEvaluation, SHORT_TEXT
from src.engine.eligibility import EligibilityEngine
from src.services.textract_service import TextractService
from src.services.bedrock_service import BedrockVisionService
from src.services.pdf_service import ClaimPdfService
from src.services import source_watch, usage_guard
from src.fixtures import DEMO_FIXTURES

MAX_IMAGE_BYTES = 4 * 1024 * 1024  # after base64 decoding; the frontend downsizes photos first
MAX_IMAGE_B64_CHARS = 6 * 1024 * 1024

app = FastAPI(
    title="RemedyAI API",
    description="Evidence-Grounded Consumer Claim Preparation Engine",
    version="1.2.0",
)

# No CORS: the site and the API share one origin (CloudFront in AWS, the Vite proxy locally),
# so other websites' pages can't read API responses.

engine = EligibilityEngine()
textract_service = TextractService()
bedrock_service = BedrockVisionService()
pdf_service = ClaimPdfService()


class ExtractRequest(BaseModel):
    receipt_base64: Optional[str] = Field(default=None, max_length=MAX_IMAGE_B64_CHARS)
    defect_image_base64: Optional[str] = Field(default=None, max_length=MAX_IMAGE_B64_CHARS)
    product_hint: Optional[str] = Field(default=None, max_length=SHORT_TEXT)


class GeneratePackageRequest(BaseModel):
    case: NormalizedCase
    # Ignored. Older clients sent their copy of the evaluation; the server always re-evaluates,
    # so a PDF can only state what the engine itself determined.
    evaluation: Optional[Any] = None


def _origin_secret() -> str:
    return os.getenv("ORIGIN_VERIFY_SECRET", "")


def _from_cloudfront(request: Request) -> bool:
    secret = _origin_secret()
    return bool(secret) and hmac.compare_digest(request.headers.get("x-origin-verify", ""), secret)


@app.middleware("http")
async def require_cloudfront(request: Request, call_next):
    """
    In AWS the API is only served through CloudFront, which adds a secret header. Requests sent
    straight to the API Gateway URL are refused, so they can't skip CloudFront's security headers
    or forge the viewer address used by the per-visitor limit. Disabled when no secret is set
    (local development and tests).
    """
    if _origin_secret() and not _from_cloudfront(request):
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})
    return await call_next(request)


def client_ip(request: Request) -> Optional[str]:
    """
    The visitor's IP. CloudFront-Viewer-Address is trusted only on requests proven to come from
    CloudFront (which sets it and cannot be told otherwise by the client); otherwise the socket peer.
    """
    addr = request.headers.get("cloudfront-viewer-address")
    if addr and _from_cloudfront(request):
        return addr.rsplit(":", 1)[0].strip("[]")
    return request.client.host if request.client else None


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "RemedyAI",
        "version": app.version,
        "policy": "Closed-World Evidence Policy",
        "knowledge_records": sorted(engine.records.keys()),
    }


@app.get("/api/fixtures")
def get_fixtures():
    """Returns the predefined one-click demo fixtures, validated, with receipt/photo marked as sample data."""
    return {k: NormalizedCase(**v).model_dump() for k, v in DEMO_FIXTURES.items()}


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


@app.post("/api/extract")
def extract_evidence(req: ExtractRequest, request: Request):
    """
    Reads a receipt photo with Amazon Textract (AnalyzeExpense) and a defect photo with
    Amazon Bedrock. Nothing is stored. The user reviews and corrects the result before
    anything is evaluated.
    """
    receipt_bytes = _decode_image(req.receipt_base64, "Receipt image") if req.receipt_base64 else None
    defect_bytes = _decode_image(req.defect_image_base64, "Defect photo") if req.defect_image_base64 else None
    if not receipt_bytes and not defect_bytes:
        raise HTTPException(status_code=400, detail="Attach a receipt photo, a defect photo, or both.")
    try:
        usage_guard.consume(int(receipt_bytes is not None) + int(defect_bytes is not None), client_ip(request))
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


def _safe_filename(case_id: str) -> str:
    return (re.sub(r"[^A-Za-z0-9_-]", "", case_id)[:64] or "case")


@app.post("/api/generate-package")
def generate_claim_package(req: GeneratePackageRequest):
    """
    Builds the claim PDF from the engine's own evaluation of the case. Any evaluation sent by the
    client is ignored. Refused while a hard consistency check is unconfirmed.
    """
    evaluation = engine.evaluate(req.case, source_status=source_watch.load_status())
    if not evaluation.pdf_allowed:
        raise HTTPException(
            status_code=409,
            detail="Please confirm the highlighted details before the claim PDF is prepared.",
        )
    try:
        pdf_bytes = pdf_service.generate_pdf(req.case, evaluation)
    except Exception as e:
        print(f"PDF generation failed: {type(e).__name__}")
        raise HTTPException(status_code=500, detail="The claim PDF could not be generated. Please try again.")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="RemedyAI_Claim_{_safe_filename(req.case.case_id)}.pdf"'},
    )
