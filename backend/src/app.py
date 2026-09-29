from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import base64
from datetime import datetime, timezone

from backend.src.models.schemas import NormalizedCase, RemedyEvaluation
from backend.src.engine.eligibility import EligibilityEngine
from backend.src.services.textract_service import TextractService
from backend.src.services.bedrock_service import BedrockVisionService
from backend.src.services.pdf_service import ClaimPdfService
from backend.src.fixtures import DEMO_FIXTURES

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


@app.post("/api/intake", response_model=NormalizedCase)
def process_intake(request: IntakeRequest):
    """
    Intake pipeline: parses receipt and defect imagery via Amazon Textract and Amazon Bedrock
    to assemble a NormalizedCase. When no image is supplied, no visual evidence is recorded.
    """
    case_id = request.case_id or f"case_{int(datetime.now(timezone.utc).timestamp())}"

    receipt_data = None
    if request.receipt_base64:
        try:
            image_bytes = base64.b64decode(request.receipt_base64)
            receipt_data = textract_service.analyze_receipt_bytes(image_bytes)
        except Exception as e:
            print(f"Receipt extraction failed: {e}")

    visual_evidence = None
    if request.defect_image_base64:
        try:
            image_bytes = base64.b64decode(request.defect_image_base64)
            visual_evidence = bedrock_service.analyze_defect_image(
                image_bytes, product_hint=request.product_name
            )
        except Exception as e:
            print(f"Bedrock vision analysis failed: {e}")

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


@app.post("/api/evaluate", response_model=RemedyEvaluation)
def evaluate_coverage(case: NormalizedCase):
    """
    Evaluates submitted case evidence against the verified primary source corpus.
    Closed-world: returns NO VERIFIED COVERAGE FOUND if no source record matches.
    """
    return engine.evaluate(case)


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
