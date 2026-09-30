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


import pytest


@pytest.mark.parametrize(
    "text",
    [
        "Camera broken <b>",  # used to crash the PDF build
        'Camera broken <img src="/etc/hostname" width="200" height="120"/>',  # used to load a server file
        'Camera broken <link href="https://evil.example">click here</link>',  # used to inject a link
        "Tom & Jerry's \"TV\" < 5 > 3",
    ],
)
def test_pdf_treats_user_text_as_text(text):
    engine = EligibilityEngine()
    case = NormalizedCase(
        case_id="case_inject",
        product_name=f"Apple iPhone 14 Plus {text}",
        purchase_date="2023-11-24",
        failure_date="2026-08-30",
        evaluation_date="2026-09-29",
        retailer=text,
        defect_description=f"Rear camera shows no preview. {text}",
    )
    pdf = ClaimPdfService().generate_pdf(case, engine.evaluate(case))
    assert pdf.startswith(b"%PDF")
    assert b"/Subtype /Image" not in pdf
    assert b"evil.example" not in pdf or b"/URI (https://evil.example)" not in pdf


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
