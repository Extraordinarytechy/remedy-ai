"""Mac mini (2023) no-power program and Apple's one-year limited warranty (iPhone 18 Pro era)."""
import pytest

from src.engine.eligibility import EligibilityEngine
from src.models.schemas import NormalizedCase, VisualDefectEvidence

AS_OF = "2026-09-30"


@pytest.fixture
def engine():
    return EligibilityEngine()


def case(**overrides):
    base = dict(
        case_id="t",
        product_name="Generic",
        purchase_date="2025-01-10",
        failure_date="2026-09-01",
        evaluation_date=AS_OF,
        purchase_country="US",
        defect_description="Stopped working.",
    )
    base.update(overrides)
    return NormalizedCase(**base)


# ---------------------------------------------------------------------------
# Mac mini (2023, M2) Service Program for No Power Issue
# ---------------------------------------------------------------------------
def test_mac_mini_m2_no_power_matches(engine):
    res = engine.evaluate(case(product_name="Apple Mac mini M2", defect_description="It won't turn on at all."))
    route = next(r for r in res.matched_routes if r.route_id == "apple_mac_mini_2023_no_power_2025")
    assert route.status == "PENDING_SERIAL_VERIFICATION"
    assert route.deadline == "2028-01-10"  # 3 years from the 2025-01-10 sale
    assert "serial number checker" in route.recommended_action


@pytest.mark.parametrize("name", ["Mac mini M2 Pro", "Mac mini M4", "Mac mini (2024)"])
def test_other_mac_mini_models_excluded(engine, name):
    res = engine.evaluate(case(product_name=name, defect_description="No power"))
    assert all(r.route_id != "apple_mac_mini_2023_no_power_2025" for r in res.matched_routes)


def test_mac_mini_sold_before_manufacturing_window(engine):
    res = engine.evaluate(case(product_name="Mac mini (2023)", purchase_date="2024-03-01", defect_description="does not power on"))
    assert all(r.route_id != "apple_mac_mini_2023_no_power_2025" for r in res.matched_routes)
    assert any("manufacturing window" in n for n in res.notes)


MAC_MINI = "apple_mac_mini_2023_no_power_2025"


def test_plain_mac_mini_is_not_assumed_to_be_the_2023_model(engine):
    # "Mac mini" alone could be an M1 or M4 model, which the program doesn't cover.
    res = engine.evaluate(case(product_name="Mac mini", purchase_date="2023-03-01", failure_date="2026-09-20",
                               defect_description="Does not power on"))
    assert all(r.route_id != MAC_MINI for r in res.matched_routes)
    reason = next(r for r in res.no_match_reasons if r.code.startswith("repair_program"))
    assert reason.code == "repair_program_model_unclear"
    assert "Mac mini (2023, M2 chip)" in reason.message


def test_mac_mini_2023_bought_before_the_affected_units_were_made(engine):
    res = engine.evaluate(case(product_name="Mac mini (2023)", purchase_date="2023-03-01", failure_date="2026-09-20",
                               defect_description="Does not power on"))
    assert all(r.route_id != MAC_MINI for r in res.matched_routes)
    assert any("manufacturing window" in n for n in res.notes)
    reason = next(r for r in res.no_match_reasons if r.code.startswith("repair_program"))
    assert reason.code == "repair_program_window"
    assert "16 Jun 2024" in reason.message


@pytest.mark.parametrize("name", ["Mac mini (2023)", "Mac mini M2", "Apple Mac mini (M2, 2023)"])
def test_mac_mini_2023_bought_in_the_window_is_pending_serial_check(engine, name):
    res = engine.evaluate(case(product_name=name, purchase_date="2024-08-01", failure_date="2026-09-20",
                               defect_description="Does not power on"))
    route = next(r for r in res.matched_routes if r.route_id == MAC_MINI)
    assert route.status == "PENDING_SERIAL_VERIFICATION"


def test_mac_mini_other_symptom_not_matched(engine):
    res = engine.evaluate(case(product_name="Mac mini M2", defect_description="Fan is loud"))
    assert all(r.route_id != "apple_mac_mini_2023_no_power_2025" for r in res.matched_routes)


# ---------------------------------------------------------------------------
# Apple One (1) Year Limited Warranty (U.S.)
# ---------------------------------------------------------------------------
WARRANTY = "apple_one_year_limited_warranty_ios_us"


def test_new_iphone_18_pro_is_under_apple_warranty(engine):
    res = engine.evaluate(case(product_name="Apple iPhone 18 Pro", purchase_date="2026-09-18", failure_date="2026-09-28",
                               defect_description="Screen flickers"))
    assert res.has_coverage is True
    route = res.matched_routes[0]
    assert route.route_id == WARRANTY
    assert route.route_type == "manufacturer_warranty"
    assert route.deadline == "2027-09-18"
    assert route.days_left == 353
    assert not any("not part of the RemedyAI source corpus" in n for n in res.notes)


def test_warranty_not_applied_outside_us(engine):
    res = engine.evaluate(case(product_name="Apple iPhone 18 Pro", purchase_country="IN", purchase_date="2026-09-18",
                               failure_date="2026-09-28"))
    assert all(r.route_id != WARRANTY for r in res.matched_routes)


def test_warranty_expired_claim_gives_note(engine):
    res = engine.evaluate(case(product_name="iPhone 17", purchase_date="2025-09-01", failure_date="2026-08-20"))
    assert all(r.route_id != WARRANTY for r in res.matched_routes)
    assert any("warranty ended on 2026-09-01" in n for n in res.notes)


def test_fault_after_warranty_is_silent(engine):
    res = engine.evaluate(case(product_name="iPhone 16", purchase_date="2024-09-20", failure_date="2026-01-05"))
    assert all(r.route_id != WARRANTY for r in res.matched_routes)
    assert not any("Warranty" in n and "iPhone" in n for n in res.notes)


def test_visible_damage_adds_accident_caveat(engine):
    res = engine.evaluate(case(
        product_name="iPhone 18 Pro Max", purchase_date="2026-09-18", failure_date="2026-09-25",
        visual_evidence=VisualDefectEvidence(visible_physical_damage=True, physical_damage_severity="screen_cracked"),
    ))
    route = res.matched_routes[0]
    assert "accident" in route.provenance.exceptions[0]


def test_product_without_a_warranty_record_keeps_generic_warranty_note(engine):
    # A brand with no warranty record in the corpus (Samsung, Google and Apple now have one).
    res = engine.evaluate(case(product_name="OnePlus 13", purchase_date="2026-06-01", failure_date="2026-09-01"))
    assert res.has_coverage is False
    assert any("original manufacturer warranty" in n for n in res.notes)


def test_every_record_has_a_public_coverage_summary(engine):
    """The site's "What RemedyAI covers today" list is built from these; a record without one would be hidden."""
    for rid, rec in engine.records.items():
        assert rec.get("coverage_summary"), rid
        assert len(rec["coverage_summary"]) <= 160, rid
