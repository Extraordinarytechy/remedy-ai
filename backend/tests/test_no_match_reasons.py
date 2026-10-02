"""Why nothing matched: one plain reason per option type, taken from the engine's own data."""
import pytest

from src.engine.eligibility import EligibilityEngine
from src.models.schemas import NormalizedCase

AS_OF = "2026-09-29"


@pytest.fixture(scope="module")
def engine():
    return EligibilityEngine()


def case(**overrides):
    base = dict(
        case_id="t",
        product_name="Generic Product",
        purchase_date="2024-09-25",
        failure_date="2026-09-20",
        evaluation_date=AS_OF,
        purchase_country="US",
        defect_description="Phone restarts on its own",
    )
    base.update(overrides)
    return NormalizedCase(**base)


def codes(res):
    return [r.code for r in res.no_match_reasons]


def message(res, code):
    return next(r.message for r in res.no_match_reasons if r.code == code)


def test_two_year_old_iphone_in_the_us(engine):
    res = engine.evaluate(case(product_name="iPhone 16"))
    assert res.matched_routes == []
    assert codes(res) == ["maker_warranty_ended", "no_repair_program", "card_not_covered", "consumer_law_uk_only"]
    assert message(res, "maker_warranty_ended") == (
        "Apple's 1-year warranty ended on 25 Sep 2025, 1 year after the purchase date."
    )
    assert message(res, "card_not_covered") == "Card benefit: RemedyAI checks Visa Infinite cards used for U.S. purchases only."
    assert message(res, "consumer_law_uk_only") == "Consumer law: RemedyAI covers purchases from UK stores only so far."
    # The older fields stay as they were, so existing clients keep working.
    assert "NO VERIFIED COVERAGE FOUND" in res.unmatched_reason
    assert res.next_steps


def test_iphone_bought_in_india_names_the_countries_covered(engine):
    res = engine.evaluate(case(product_name="iPhone 17", purchase_country="IN",
                               purchase_date="2026-02-01", failure_date="2026-09-01"))
    assert message(res, "maker_warranty_country") == (
        "RemedyAI has Apple's warranty for purchases in the U.S. only. Purchases in India are not covered yet."
    )


def test_pixel_in_australia_lists_us_and_canada(engine):
    res = engine.evaluate(case(product_name="Pixel 10", purchase_country="AU",
                               purchase_date="2026-02-01", failure_date="2026-09-01"))
    assert "for purchases in the U.S. and Canada only. Purchases in Australia" in message(res, "maker_warranty_country")


def test_brand_without_a_warranty_record(engine):
    res = engine.evaluate(case(product_name="OnePlus 13", purchase_date="2026-02-01", failure_date="2026-09-01"))
    assert message(res, "no_maker_warranty") == (
        "RemedyAI has no maker's warranty that names this product. It covers some Apple, Google and Samsung products so far."
    )


def test_pixel_9_pro_with_another_fault(engine):
    res = engine.evaluate(case(product_name="Pixel 9 Pro", purchase_date="2024-10-05", defect_description="Battery drains fast"))
    assert "repair_program_other_fault" in codes(res)
    assert message(res, "repair_program_other_fault").startswith(
        "Pixel 9 Pro & Pixel 9 Pro XL Extended Repair Program covers only this fault: A vertical line"
    )


def test_repair_program_window_closed(engine):
    res = engine.evaluate(case(product_name="iPhone 14 Plus", purchase_date="2023-06-01", failure_date="2026-05-01",
                               evaluation_date="2026-07-01", defect_description="Rear camera shows no preview"))
    assert message(res, "repair_program_window").endswith("its 3-year window closed on 1 Jun 2026.")


def test_card_reasons_follow_the_card_rules(engine):
    inside = engine.evaluate(case(product_name="BrandX Blender", payment_method="Visa Infinite",
                                  purchase_date="2026-03-01", failure_date="2026-09-01"))
    assert "card_inside_warranty" in codes(inside)
    assert "during the original 1-year warranty" in message(inside, "card_inside_warranty")

    ended = engine.evaluate(case(product_name="BrandX Blender", payment_method="Visa Infinite",
                                 purchase_date="2022-01-01", failure_date="2025-06-01"))
    assert message(ended, "card_window_ended") == "Card benefit: the Visa Infinite extra year ended on 1 Jan 2024."

    too_long = engine.evaluate(case(product_name="BrandX Blender", payment_method="Visa Infinite",
                                    original_warranty_years=5, purchase_date="2022-01-01", failure_date="2025-06-01"))
    assert "card_warranty_too_long" in codes(too_long)

    abroad = engine.evaluate(case(product_name="BrandX Blender", payment_method="Visa Infinite", purchase_country="CA"))
    assert "card_not_covered" in codes(abroad)


def test_uk_time_limit_ended(engine):
    res = engine.evaluate(case(product_name="BrandX Kettle", purchase_country="GB", uk_region="scotland",
                               purchase_date="2021-01-10", failure_date="2026-05-01"))
    assert message(res, "consumer_law_time_limit") == "The 5-year time limit to claim under UK consumer law ended on 10 Jan 2026."


def test_accessory_reason_replaces_the_device_reasons(engine):
    res = engine.evaluate(case(product_name="iPhone 17 case", purchase_date="2026-02-01", failure_date="2026-09-01"))
    assert codes(res)[0] == "accessory"
    assert not any(c.startswith(("maker_warranty", "no_maker", "repair_program", "no_repair")) for c in codes(res))


def test_reasons_never_claim_coverage(engine):
    res = engine.evaluate(case(product_name="iPhone 16"))
    for r in res.no_match_reasons:
        assert "\u2014" not in r.message
        assert "covered by" not in r.message.lower()


def test_no_reasons_when_something_matched_or_the_input_is_invalid(engine):
    matched = engine.evaluate(case(product_name="iPhone 17", purchase_date="2026-02-01", failure_date="2026-09-01"))
    assert matched.has_coverage is True
    assert matched.no_match_reasons == []
    invalid = engine.evaluate(case(purchase_date="2026-09-25", failure_date="2026-09-01"))
    assert invalid.input_error == "failure_before_purchase"
    assert invalid.no_match_reasons == []


def test_espresso_demo_keeps_its_closed_world_message(engine):
    res = engine.evaluate(case(product_name="BrandX Espresso Maker", purchase_date="2023-01-10", failure_date="2026-04-12",
                               payment_method="Cash", defect_description="Pump stopped building pressure."))
    assert "NO VERIFIED COVERAGE FOUND" in res.unmatched_reason
    assert codes(res) == ["no_maker_warranty", "no_repair_program", "card_not_covered", "consumer_law_uk_only"]
