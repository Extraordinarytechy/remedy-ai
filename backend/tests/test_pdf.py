from src.models.schemas import NormalizedCase, VisualDefectEvidence
from src.engine.eligibility import EligibilityEngine
from src.services.pdf_service import ClaimPdfService


def test_pdf_generation_eligible_case():
    engine = EligibilityEngine()
    case = NormalizedCase(
        case_id="case_apple_test",
        product_name="Apple iPhone 14 Plus",
        purchase_date="2023-11-24",
        failure_date="2026-08-30",
        evaluation_date="2026-09-29",
        purchase_country="US",
        retailer="Best Buy",
        payment_method="Visa Infinite",
        defect_description="Rear camera shows no preview",
        visual_evidence=VisualDefectEvidence(
            anomaly_detected=True,
            visible_physical_damage=False,
            physical_damage_severity="none",
            visual_observations=["Display intact, acoustic mesh clean"],
        ),
    )
    evaluation = engine.evaluate(case)
    pdf_service = ClaimPdfService()
    pdf_bytes = pdf_service.generate_pdf(case, evaluation)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")


def test_pdf_generation_unmatched_case():
    engine = EligibilityEngine()
    case = NormalizedCase(
        case_id="case_unknown_test",
        product_name="Generic Blender",
        purchase_date="2020-01-01",
        failure_date="2023-01-01",
        purchase_country="US",
        defect_description="Motor stopped spinning",
    )
    evaluation = engine.evaluate(case)
    pdf_service = ClaimPdfService()
    pdf_bytes = pdf_service.generate_pdf(case, evaluation)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")
