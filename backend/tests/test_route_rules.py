"""
Rules every route must follow: deadlines measured against the claim date, the record's country
scope, the record's own delisting flag, product matching that ignores accessories, and claim
letters only for options the user can act on.
"""
import pytest

from src.engine.eligibility import EligibilityEngine, is_actionable, parse_date
from src.models.schemas import NormalizedCase

AS_OF = "2026-09-29"
VISA = "visa_infinite_extended_warranty_us"
WARRANTY = "apple_one_year_limited_warranty_ios_us"
IPHONE12 = "apple_iphone12_no_sound_2021"
MAC_MINI = "apple_mac_mini_2023_no_power_2025"
UK = "uk_cra_2015_goods"


@pytest.fixture(scope="module")
def engine():
    return EligibilityEngine()


def case(**overrides):
    base = dict(
        case_id="t", product_name="Sony WH-1000XM5 headphones", purchase_date="2025-03-14",
        failure_date="2026-09-05", purchase_country="US", payment_method="Visa Infinite",
        original_warranty_years=1.0, defect_description="Hinge cracked", evaluation_date=AS_OF,
    )
    base.update(overrides)
    return NormalizedCase(**base)


def ids(res):
    return [r.route_id for r in res.matched_routes]


# --- Visa Infinite -------------------------------------------------------------
def test_visa_inside_extended_period_matches(engine):
    assert ids(engine.evaluate(case())) == [VISA]


def test_visa_after_extended_period_is_a_note_not_a_match(engine):
    # The fault was inside the extended year (2022), but that year ended on 2023-01-01.
    res = engine.evaluate(case(purchase_date="2021-01-01", failure_date="2022-06-01"))
    assert VISA not in ids(res)
    assert any("ended on 2023-01-01" in n for n in res.notes)


def test_visa_us_benefit_does_not_apply_outside_the_us(engine):
    for country in ("GB", "IN", "CA"):
        res = engine.evaluate(case(purchase_country=country, uk_region="england_wales" if country == "GB" else None))
        assert VISA not in ids(res)


# --- Delisted and unverified sources ------------------------------------------
def test_delisted_program_is_never_presented_as_live(engine):
    # Inside the 3-year window, and no Source Watch data at all.
    res = engine.evaluate(case(
        product_name="Apple iPhone 12", purchase_date="2021-02-10", failure_date="2023-08-15",
        evaluation_date="2023-08-20", payment_method=None, defect_description="No sound from the receiver during calls",
    ))
    route = next(r for r in res.matched_routes if r.route_id == IPHONE12)
    assert route.status == "NEEDS_REVERIFICATION"
    assert not is_actionable(route)
    assert res.pdf_allowed is False


def test_unreadable_source_status_marks_routes_unverified(engine):
    res = engine.evaluate(case(), source_status={}, source_status_unavailable=True)
    assert [r.status for r in res.matched_routes] == ["NEEDS_REVERIFICATION"]
    assert "could not load" in res.matched_routes[0].provenance.exceptions[0]
    assert res.pdf_allowed is False


def test_readable_source_status_keeps_routes(engine):
    res = engine.evaluate(case(), source_status={}, source_status_unavailable=False)
    assert [r.status for r in res.matched_routes] == ["POTENTIALLY_ELIGIBLE"]
    assert res.pdf_allowed is True


# --- Product matching -----------------------------------------------------------
@pytest.mark.parametrize("name", [
    "Apple iPhone 18 Pro case", "iPhone 18 Pro Max screen protector", "MagSafe charger for iPhone",
    "Samsung TV with the Apple TV app", "Lightning cable for iPad",
])
def test_accessories_and_apps_do_not_match_apple_hardware(engine, name):
    res = engine.evaluate(case(product_name=name, purchase_date="2026-09-18", failure_date="2026-09-25", payment_method=None))
    assert WARRANTY not in ids(res)


def test_another_brand_named_by_the_user_rules_out_apple(engine):
    res = engine.evaluate(case(product_name="iPhone 18 Pro clone", product_brand="Generic", purchase_date="2026-09-18",
                               failure_date="2026-09-25", payment_method=None))
    assert WARRANTY not in ids(res)


def test_device_names_match_whole_words_only(engine):
    res = engine.evaluate(case(product_name="iPhone 120 toy", purchase_date="2021-02-10", failure_date="2023-08-15",
                               evaluation_date="2023-08-20", payment_method=None, defect_description="No sound on calls"))
    assert IPHONE12 not in ids(res)


def test_real_apple_device_still_matches(engine):
    res = engine.evaluate(case(product_name="Apple iPhone 18 Pro", product_brand="Apple", purchase_date="2026-09-18",
                               failure_date="2026-09-25", payment_method=None))
    assert ids(res) == [WARRANTY]


# --- Manufacturing window -------------------------------------------------------
def test_purchase_long_after_the_affected_units_gets_a_caveat(engine):
    res = engine.evaluate(case(product_name="Mac mini (2023)", purchase_date="2026-01-15", failure_date="2026-09-01",
                               payment_method=None, defect_description="It won't turn on (no power)"))
    route = next(r for r in res.matched_routes if r.route_id == MAC_MINI)
    assert "more than a year after the last affected units were made" in route.provenance.exceptions[0]
    assert route.status == "PENDING_SERIAL_VERIFICATION"  # Apple's serial check still decides


# --- UK region ------------------------------------------------------------------
def uk(**overrides):
    return case(product_name="Samsung TV", purchase_country="GB", payment_method=None, retailer="Currys",
                defect_description="Lines on screen", **overrides)


def test_uk_without_region_is_held_once_scotland_would_have_ended(engine):
    # 5.5 years after purchase: inside 6 years, outside Scotland's 5.
    res = engine.evaluate(uk(purchase_date="2021-04-01", failure_date="2026-01-10"))
    route = next(r for r in res.matched_routes if r.route_id == UK)
    assert route.status == "NEEDS_CONFIRMATION"
    assert "Choose which part of the UK" in route.provenance.exceptions[0]
    assert res.pdf_allowed is False


def test_uk_without_region_inside_five_years_is_not_held(engine):
    res = engine.evaluate(uk(purchase_date="2023-07-20", failure_date="2026-08-22"))
    assert [r.status for r in res.matched_routes] == ["POTENTIALLY_ELIGIBLE"]
    assert res.pdf_allowed is True


def test_uk_with_region_is_not_held(engine):
    res = engine.evaluate(uk(purchase_date="2021-04-01", failure_date="2026-01-10", uk_region="england_wales"))
    assert [r.status for r in res.matched_routes] == ["POTENTIALLY_ELIGIBLE"]


# --- Dates ----------------------------------------------------------------------
@pytest.mark.parametrize("bad", ["03/04/2024", "2024/03/04", "4 March 2024", "2024-3-4", ""])
def test_case_dates_must_be_iso(bad):
    with pytest.raises(ValueError):
        parse_date(bad)
