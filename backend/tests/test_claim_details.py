"""Who a claim goes to, the UK 30-day right to reject, symptom precision, input limits and evidence masking."""
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from src.app import app
from src.engine.eligibility import EligibilityEngine
from src.models.schemas import NormalizedCase

client = TestClient(app)
engine = EligibilityEngine()


def case(**kw):
    body = dict(case_id="t", product_name="Generic Product", purchase_date="2024-01-01", failure_date="2026-01-01",
                evaluation_date="2026-10-01", purchase_country="US", defect_description="Stopped working.")
    body.update(kw)
    return NormalizedCase(**body)


def routes(c):
    return {r.route_id: r for r in engine.evaluate(c).matched_routes}


# --- UK consumer law --------------------------------------------------------------------------
def test_uk_purchase_within_30_days_gets_the_right_to_reject():
    c = case(purchase_country="GB", uk_region="england_wales", retailer="Currys", product_name="Kettle",
             purchase_date="2026-09-21", failure_date="2026-09-28", evaluation_date="2026-10-01")
    r = routes(c)["uk_cra_2015_goods"]
    assert "reject" in r.recommended_action and "full refund" in r.recommended_action
    assert "10 days ago" in r.recommended_action
    assert any("30-day right to reject" in e for e in r.provenance.exceptions)
    assert r.claim_to == "Currys"


def test_uk_purchase_after_30_days_asks_for_repair_or_replacement():
    c = case(purchase_country="GB", uk_region="england_wales", retailer="Currys",
             purchase_date="2025-01-10", failure_date="2026-09-20", evaluation_date="2026-10-01")
    r = routes(c)["uk_cra_2015_goods"]
    assert "repair or replacement" in r.recommended_action
    assert not any("30-day right to reject" in e for e in r.provenance.exceptions)


def test_uk_claim_goes_to_the_store_even_without_a_name():
    c = case(purchase_country="GB", uk_region="scotland", purchase_date="2025-01-10", failure_date="2026-09-20")
    assert routes(c)["uk_cra_2015_goods"].claim_to == "The store that sold it"


# --- Card benefit -----------------------------------------------------------------------------
def test_visa_claim_goes_to_the_benefit_administrator():
    c = case(product_name="Sony WH-1000XM5 headphones", payment_method="Visa Infinite",
             purchase_date="2025-03-01", failure_date="2026-09-15", original_warranty_years=1)
    r = routes(c)["visa_infinite_extended_warranty_us"]
    assert "benefit administrator" in r.claim_to
    assert "may be earlier" in r.deadline_label


# --- Symptom precision ------------------------------------------------------------------------
def test_pixel_program_needs_a_vertical_line():
    base = dict(product_name="Google Pixel 9 Pro", purchase_date="2024-10-05", failure_date="2026-09-20")
    assert "google_pixel9pro_display_2025" not in routes(case(**base, defect_description="A horizontal pink line across the screen"))
    assert "google_pixel9pro_display_2025" in routes(case(**base, defect_description="A vertical pink line on the screen"))


# --- API input handling -----------------------------------------------------------------------
def test_validation_errors_name_fields_only():
    secret = "my-home-address-12-Example-Road"
    res = client.post("/api/evaluate", json={"case_id": "t", "product_name": secret, "purchase_date": "bad"})
    assert res.status_code == 422
    body = res.json()
    assert isinstance(body["detail"], str) and "failure_date" in body["fields"]
    assert secret not in res.text and "pydantic" not in res.text.lower()


def test_confirmed_checks_are_length_limited():
    from src.app import DEMO_FIXTURES

    payload = {**DEMO_FIXTURES["case1_apple_iphone14plus"], "confirmed_checks": ["x" * 65]}
    assert client.post("/api/evaluate", json=payload).status_code == 422


def test_textract_output_is_held_to_the_api_limits():
    from src.models.schemas import LONG_TEXT, SHORT_TEXT
    from src.services.textract_service import TextractService

    svc = TextractService.__new__(TextractService)
    long = "A" * 5000
    response = {"ExpenseDocuments": [{
        "SummaryFields": [
            {"Type": {"Text": "VENDOR_NAME"}, "ValueDetection": {"Text": long, "Confidence": 99}},
            {"Type": {"Text": "PAYMENT_METHOD"}, "ValueDetection": {"Text": long}},
        ],
        "LineItemGroups": [{"LineItems": [{"LineItemExpenseFields": [
            {"Type": {"Text": "ITEM"}, "ValueDetection": {"Text": long}}]}]}],
    }]}
    r = svc._parse_expense_response(response)
    assert len(r.store_name) <= SHORT_TEXT and len(r.payment_type) <= SHORT_TEXT
    assert len(r.item_description) <= LONG_TEXT
    assert all(len(v) <= 500 for v in r.raw_fields.values())


# --- Evidence masking -------------------------------------------------------------------------
def test_redaction_masks_account_ids_but_keeps_request_ids():
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    from redact_evidence import redact

    assert redact("arn:aws:iam::248189935724:user/x") == "arn:aws:iam::2481****5724:user/x"
    assert redact('"Account": "248189935724"') == '"Account": "2481****5724"'
    assert redact('"UserId": "AIDATTSKF4BWMSUYKT4XA"') == '"UserId": "AIDA****************"'
    assert redact("remedy-ai-site-248189935724") == "remedy-ai-site-2481****5724"
    request_id = "3f2a1b2c-1234-4abc-9def-248189935724"
    assert redact(request_id) == request_id
    assert redact("a@example.com") == "<redacted-email>"
