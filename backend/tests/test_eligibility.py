import pytest
from src.models.schemas import NormalizedCase, VisualDefectEvidence
from src.engine.eligibility import EligibilityEngine

# Fixed "claim date" so window checks are deterministic regardless of when tests run.
AS_OF = "2026-09-29"


@pytest.fixture
def engine():
    return EligibilityEngine()


def make_case(**overrides):
    base = dict(
        case_id="case_test",
        product_name="Generic Product",
        purchase_date="2024-01-01",
        failure_date="2026-01-01",
        purchase_country="US",
        defect_description="Stopped working.",
        evaluation_date=AS_OF,
    )
    base.update(overrides)
    return NormalizedCase(**base)


# ---------------------------------------------------------------------------
# Apple iPhone 14 Plus rear camera program (active, serial check required)
# ---------------------------------------------------------------------------
def test_iphone14plus_pending_serial_verification(engine):
    case = make_case(
        product_name="Apple iPhone 14 Plus",
        product_model="iPhone 14 Plus",
        purchase_date="2023-11-24",
        failure_date="2026-08-30",
        defect_description="Rear camera shows a black screen with no preview.",
    )
    res = engine.evaluate(case)
    assert res.has_coverage is True
    assert res.evaluation_date == AS_OF
    route = res.matched_routes[0]
    assert route.route_id == "apple_iphone14plus_rear_camera_2024"
    assert route.status == "PENDING_SERIAL_VERIFICATION"
    assert "serial number checker" in route.recommended_action
    assert "2026-11-24" in route.provenance.evidence[0]  # window end = purchase + 3 years


def test_iphone14plus_refund_when_already_paid(engine):
    case = make_case(
        product_name="iPhone 14 Plus",
        purchase_date="2023-11-24",
        failure_date="2026-05-01",
        defect_description="Rear camera had no preview; I paid for a camera repair.",
        already_paid_for_repair=True,
    )
    route = engine.evaluate(case).matched_routes[0]
    assert "refund" in route.recommended_action.lower()


def test_iphone14plus_purchased_before_manufacturing_window(engine):
    case = make_case(
        product_name="iPhone 14 Plus",
        purchase_date="2022-10-07",  # launch week, before April 10, 2023 manufacturing start
        failure_date="2024-06-01",
        evaluation_date="2024-06-15",
        defect_description="Rear camera no preview",
    )
    res = engine.evaluate(case)
    assert res.has_coverage is False
    assert any("manufacturing window" in n for n in res.notes)


def test_iphone14plus_window_closed(engine):
    case = make_case(
        product_name="iPhone 14 Plus",
        purchase_date="2023-06-01",
        failure_date="2026-05-01",
        evaluation_date="2026-07-01",  # window closed 2026-06-01
        defect_description="Rear camera shows no preview",
    )
    res = engine.evaluate(case)
    assert res.has_coverage is False
    assert any("closed on 2026-06-01" in n for n in res.notes)


def test_iphone14_pro_not_in_program(engine):
    case = make_case(
        product_name="iPhone 14 Pro",
        purchase_date="2023-11-24",
        failure_date="2026-08-30",
        defect_description="Rear camera shows no preview",
    )
    assert engine.evaluate(case).has_coverage is False


# ---------------------------------------------------------------------------
# Apple iPhone 12 no-sound program (no longer listed on Apple's index)
# ---------------------------------------------------------------------------
def test_iphone12_inside_window_is_shown_but_must_be_checked_first(engine):
    case = make_case(
        product_name="Apple iPhone 12",
        product_model="iPhone 12",
        purchase_date="2021-02-10",
        failure_date="2023-08-15",
        evaluation_date="2023-08-20",
        defect_description="No sound from receiver module when making or answering phone calls.",
    )
    res = engine.evaluate(case)
    assert res.has_coverage is True
    route = res.matched_routes[0]
    assert route.route_id == "apple_iphone12_no_sound_2021"
    # The record marks the program as no longer on Apple's list, so it is never presented as live.
    assert route.status == "NEEDS_REVERIFICATION"
    assert res.pdf_allowed is False
    assert "https://support.apple.com" in route.provenance.source_url
    assert any("no longer listed" in e for e in route.provenance.exceptions)


def test_iphone12_window_closed_as_of_today(engine):
    case = make_case(
        product_name="Apple iPhone 12",
        purchase_date="2021-02-10",
        failure_date="2023-08-15",
        defect_description="Receiver does not emit sound during calls",
    )
    res = engine.evaluate(case)
    assert res.has_coverage is False
    assert any("closed on 2024-02-10" in n for n in res.notes)


def test_iphone12_mini_excluded(engine):
    case = make_case(
        product_name="Apple iPhone 12 mini",
        purchase_date="2021-02-10",
        failure_date="2023-08-15",
        evaluation_date="2023-08-20",
        defect_description="Receiver audio failure",
    )
    res = engine.evaluate(case)
    assert res.has_coverage is False
    assert "NO VERIFIED COVERAGE FOUND" in (res.unmatched_reason or "")


def test_iphone12_loudspeaker_issue_is_not_receiver(engine):
    case = make_case(
        product_name="Apple iPhone 12",
        purchase_date="2021-02-10",
        failure_date="2023-08-15",
        evaluation_date="2023-08-20",
        defect_description="Bottom loudspeaker crackles when playing music.",
    )
    assert engine.evaluate(case).has_coverage is False


def test_cracked_screen_caveat_added(engine):
    case = make_case(
        product_name="iPhone 14 Plus",
        purchase_date="2023-11-24",
        failure_date="2026-08-30",
        defect_description="Rear camera no preview",
        visual_evidence=VisualDefectEvidence(physical_damage_severity="severe"),
    )
    route = engine.evaluate(case).matched_routes[0]
    assert "Visible physical damage" in route.provenance.exceptions[0]


# ---------------------------------------------------------------------------
# Visa Infinite extended warranty
# ---------------------------------------------------------------------------
def test_visa_infinite_extended_warranty(engine):
    case = make_case(
        product_name="Sony WH-1000XM5 Wireless Headphones",
        purchase_date="2025-03-14",
        failure_date="2026-09-05",
        payment_method="Visa Infinite",
        original_warranty_years=1.0,
        defect_description="Left ear cup hinge cracked under normal adjustment.",
    )
    res = engine.evaluate(case)
    assert res.has_coverage is True
    route = res.matched_routes[0]
    assert route.route_id == "visa_infinite_extended_warranty_us"
    assert route.status == "POTENTIALLY_ELIGIBLE"


def test_visa_infinite_outside_window(engine):
    case = make_case(
        purchase_date="2021-01-01",
        failure_date="2023-06-01",
        payment_method="Visa Infinite",
        original_warranty_years=1.0,
    )
    assert engine.evaluate(case).has_coverage is False


# ---------------------------------------------------------------------------
# UK Consumer Rights Act 2015
# ---------------------------------------------------------------------------
def test_uk_consumer_rights(engine):
    case = make_case(
        product_name="Samsung 55-inch 4K Smart TV",
        purchase_date="2023-07-20",
        failure_date="2026-08-22",
        purchase_country="GB",
        retailer="Currys",
        defect_description="Dark horizontal lines across the bottom of the display.",
    )
    res = engine.evaluate(case)
    assert res.has_coverage is True
    route = res.matched_routes[0]
    assert route.route_id == "uk_cra_2015_goods"
    assert any("did not conform to the contract when delivered" in exc for exc in route.provenance.exceptions)
    assert "price reduction or final right to reject" in route.provenance.claim
    assert route.deadline == "2029-07-20"


def test_uk_limitation_period_expired(engine):
    case = make_case(
        purchase_date="2019-05-01",
        failure_date="2024-01-01",
        purchase_country="GB",
    )
    res = engine.evaluate(case)
    assert res.has_coverage is False
    assert any("period to make a claim" in n and "ended on 2025-05-01" in n for n in res.notes)


def test_uk_not_matched_by_retailer_name(engine):
    case = make_case(purchase_country="US", retailer="Duke's Electronics")
    assert engine.evaluate(case).has_coverage is False


# ---------------------------------------------------------------------------
# Closed-world fallback and input validation
# ---------------------------------------------------------------------------
def test_unknown_case_closed_world_fallback(engine):
    case = make_case(
        product_name="BrandX Espresso Maker",
        purchase_date="2023-01-10",
        failure_date="2026-04-12",
        payment_method="Cash",
        defect_description="Pump stopped building pressure.",
    )
    res = engine.evaluate(case)
    assert res.has_coverage is False
    assert res.matched_routes == []
    assert "NO VERIFIED COVERAGE FOUND" in res.unmatched_reason
    assert res.next_steps


def test_within_original_warranty_note(engine):
    case = make_case(purchase_date="2026-03-01", failure_date="2026-09-01")
    res = engine.evaluate(case)
    assert res.has_coverage is False
    assert any("original manufacturer warranty" in n for n in res.notes)


def test_failure_before_purchase_is_invalid(engine):
    res = engine.evaluate(make_case(purchase_date="2025-05-01", failure_date="2025-01-01"))
    assert res.has_coverage is False
    assert res.unmatched_reason.startswith("INVALID INPUT")
    assert res.input_error == "failure_before_purchase"


def test_failure_in_future_is_invalid(engine):
    res = engine.evaluate(make_case(failure_date="2027-01-01"))
    assert res.has_coverage is False
    assert res.unmatched_reason.startswith("INVALID INPUT")
    assert res.input_error == "future_date"


@pytest.mark.parametrize("purchase", ["1900-01-01", "0001-01-01"])
def test_purchase_more_than_30_years_ago_is_invalid(engine, purchase):
    res = engine.evaluate(make_case(purchase_date=purchase))
    assert res.has_coverage is False
    assert res.matched_routes == []
    assert res.unmatched_reason.startswith("INVALID INPUT")
    assert res.input_error == "too_old"


def test_thirty_year_boundary(engine):
    assert engine.evaluate(make_case(purchase_date="1996-09-29")).input_error is None
    assert engine.evaluate(make_case(purchase_date="1996-09-28")).input_error == "too_old"
