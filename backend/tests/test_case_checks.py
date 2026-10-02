"""Receipt vs form consistency checks, UK regions and the case timeline."""
import pytest

from src.engine.case_checks import detect_currency_marker
from src.engine.eligibility import EligibilityEngine
from src.models.schemas import NormalizedCase, ReceiptData

AS_OF = "2026-09-29"


@pytest.fixture
def engine():
    return EligibilityEngine()


def uk_case(**overrides):
    base = dict(
        case_id="case_uk",
        product_name="Apple iPhone 14 Plus 128GB",
        purchase_date="2023-11-24",
        failure_date="2025-01-30",
        evaluation_date=AS_OF,
        purchase_country="GB",
        uk_region="england_wales",
        retailer="Best Buy",
        defect_description="Screen flickers.",
    )
    base.update(overrides)
    return NormalizedCase(**base)


def textract_receipt(**overrides):
    base = dict(store_name="BEST BUY", purchase_date="2023-11-24", currency_evidence="$", source="textract")
    base.update(overrides)
    return ReceiptData(**base)


@pytest.mark.parametrize(
    "text, marker",
    [("$863.99", "$"), ("£479.00", "£"), ("GBP 479.00", "GBP"), ("Rs. 4,999", "RS"), ("863.99", None), ("CURRYS 12", None)],
)
def test_detect_currency_marker(text, marker):
    assert detect_currency_marker(text) == marker


def test_us_receipt_entered_as_uk_needs_confirmation(engine):
    """A US Best Buy receipt ($) entered as a UK purchase: the UK option is held and the PDF blocked."""
    res = engine.evaluate(uk_case(receipt_data=textract_receipt()))
    route = res.matched_routes[0]
    assert route.route_id == "uk_cra_2015_goods"
    assert route.status == "NEEDS_CONFIRMATION"
    assert res.pdf_allowed is False
    check = next(c for c in res.checks if c.id == "country_currency")
    assert check.severity == "hard" and check.confirmed is False
    assert "dollars" in check.message


def test_confirming_the_country_releases_the_pdf(engine):
    res = engine.evaluate(uk_case(receipt_data=textract_receipt(), confirmed_checks=["country_currency"]))
    assert res.pdf_allowed is True
    assert res.matched_routes[0].status == "POTENTIALLY_ELIGIBLE"
    assert next(c for c in res.checks if c.id == "country_currency").confirmed is True


def test_uk_receipt_in_pounds_raises_no_currency_check(engine):
    res = engine.evaluate(uk_case(retailer="Currys", receipt_data=textract_receipt(store_name="CURRYS", currency_evidence="£")))
    assert not [c for c in res.checks if c.id == "country_currency"]
    assert res.pdf_allowed is True


def test_default_currency_is_never_treated_as_evidence(engine):
    """ReceiptData.currency is display-only; with no printed marker there is no country check."""
    res = engine.evaluate(uk_case(retailer="Currys", receipt_data=textract_receipt(store_name="CURRYS", currency_evidence=None, currency="USD")))
    assert not [c for c in res.checks if c.id == "country_currency"]


def test_receipt_date_mismatch_blocks_the_pdf_until_confirmed(engine):
    """Deadlines are counted from the purchase date, so a different receipt date must be confirmed."""
    receipt = textract_receipt(store_name="CURRYS", currency_evidence="£", purchase_date="2023-11-20")
    res = engine.evaluate(uk_case(retailer="Currys", receipt_data=receipt))
    check = next(c for c in res.checks if c.id == "receipt_date")
    assert check.severity == "hard" and check.confirmed is False
    assert "2023-11-24" in check.confirm_label
    assert res.pdf_allowed is False
    res = engine.evaluate(uk_case(retailer="Currys", receipt_data=receipt, confirmed_checks=["receipt_date"]))
    assert res.pdf_allowed is True
    assert next(c for c in res.checks if c.id == "receipt_date").confirmed is True


def test_matching_receipt_date_raises_no_date_check(engine):
    res = engine.evaluate(uk_case(retailer="Currys", receipt_data=textract_receipt(store_name="CURRYS", currency_evidence="£")))
    assert not [c for c in res.checks if c.id == "receipt_date"]


def test_receipt_store_mismatch_is_a_soft_warning(engine):
    res = engine.evaluate(uk_case(retailer="Argos", receipt_data=textract_receipt(store_name="CURRYS", currency_evidence="£")))
    assert next(c for c in res.checks if c.id == "receipt_store").severity == "soft"
    assert res.pdf_allowed is True


def test_sample_receipts_are_not_checked(engine):
    res = engine.evaluate(uk_case(receipt_data=textract_receipt(source="sample")))
    assert res.checks == []


# A March 2021 purchase needs a model that was on sale then: iPhone 12 went on sale in October 2020.
OLDER_PHONE = "Apple iPhone 12 128GB"


def test_scotland_uses_five_years(engine):
    kwargs = dict(product_name=OLDER_PHONE, purchase_date="2021-03-01", failure_date="2025-01-10", evaluation_date="2026-09-29")
    assert engine.evaluate(uk_case(uk_region="scotland", **kwargs)).has_coverage is False
    assert engine.evaluate(uk_case(uk_region="england_wales", **kwargs)).has_coverage is True


def test_northern_ireland_uses_six_years(engine):
    res = engine.evaluate(uk_case(uk_region="northern_ireland", product_name=OLDER_PHONE,
                                  purchase_date="2021-03-01", failure_date="2025-01-10"))
    route = res.matched_routes[0]
    assert route.deadline == "2027-03-01"
    assert "Northern Ireland" in route.deadline_label


def test_missing_region_says_so(engine):
    route = engine.evaluate(uk_case(uk_region=None)).matched_routes[0]
    assert any("Region not given" in x for x in route.provenance.exceptions)


def test_timeline_shows_exact_dates(engine):
    res = engine.evaluate(uk_case(retailer="Currys"))
    tl = res.timeline
    assert (tl.purchase_date, tl.failure_date, tl.claim_date) == ("2023-11-24", "2025-01-30", AS_OF)
    assert tl.months_before_failure == 14.2
    route = res.matched_routes[0]
    assert route.deadline == "2029-11-24"
    assert any("fault appeared 2025-01-30" in ev for ev in route.provenance.evidence)
