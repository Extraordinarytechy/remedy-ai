"""Apple's U.S. one-year warranties for Mac, Apple Watch, and AirPods and Apple accessories (data-only records)."""
import pytest

from src.engine.eligibility import EligibilityEngine
from src.models.schemas import NormalizedCase

AS_OF = "2026-09-30"
MAC = "apple_one_year_limited_warranty_mac_us"
WATCH = "apple_one_year_limited_warranty_watch_us"
ACCESSORY = "apple_one_year_limited_warranty_accessories_us"
IOS = "apple_one_year_limited_warranty_ios_us"
APPLE_WARRANTIES = {MAC, WATCH, ACCESSORY, IOS}


@pytest.fixture(scope="module")
def engine():
    return EligibilityEngine()


def case(**overrides):
    base = dict(
        case_id="t",
        product_name="Generic",
        purchase_date="2026-02-01",
        failure_date="2026-09-20",
        evaluation_date=AS_OF,
        purchase_country="US",
        defect_description="Stopped working.",
    )
    base.update(overrides)
    return NormalizedCase(**base)


def apple_routes(res):
    return {r.route_id for r in res.matched_routes if r.route_id in APPLE_WARRANTIES}


@pytest.mark.parametrize("name", ["MacBook Air M4", "Apple MacBook Pro 14", "iMac", "Mac mini M4", "Mac Studio"])
def test_mac_models_get_the_mac_warranty(engine, name):
    res = engine.evaluate(case(product_name=name))
    assert apple_routes(res) == {MAC}
    route = next(r for r in res.matched_routes if r.route_id == MAC)
    assert route.status == "POTENTIALLY_ELIGIBLE"
    assert route.deadline == "2027-02-01"
    assert route.claim_to == "Apple Support"
    assert "liquid contact" in " ".join(route.provenance.exceptions)


@pytest.mark.parametrize("name", ["Apple Watch Series 11", "Apple Watch Ultra 3", "apple watch se"])
def test_apple_watch_gets_the_watch_warranty(engine, name):
    res = engine.evaluate(case(product_name=name))
    assert apple_routes(res) == {WATCH}
    route = next(r for r in res.matched_routes if r.route_id == WATCH)
    assert route.deadline == "2027-02-01"
    assert any("country where the watch was originally sold" in e for e in route.provenance.exceptions)


@pytest.mark.parametrize("name", [
    "AirPods Pro 3", "AirPods 4", "AirPods Max", "Magic Keyboard", "Apple Pencil Pro", "MagSafe Charger",
    "Apple Watch band", "AirPods charging case", "AirTag",
])
def test_accessories_get_the_accessory_warranty_only(engine, name):
    res = engine.evaluate(case(product_name=name))
    assert apple_routes(res) == {ACCESSORY}
    assert next(r for r in res.matched_routes if r.route_id == ACCESSORY).deadline == "2027-02-01"


@pytest.mark.parametrize("name", ["MacBook charger", "AirPods case", "iPhone 17 case", "Apple TV app", "Apple Watch strap"])
def test_third_party_style_accessories_and_apps_get_no_apple_warranty(engine, name):
    res = engine.evaluate(case(product_name=name))
    assert apple_routes(res) == set()
    assert [r.code for r in res.no_match_reasons][0] == "accessory"


def test_watch_record_never_matches_a_band(engine):
    watch = engine.records[WATCH]
    assert not engine._device_matches(case(product_name="Apple Watch band"), watch)
    assert not engine._device_matches(case(product_name="Apple Watch Series 11 band"), watch)


def test_apple_watch_edition_is_excluded(engine):
    assert apple_routes(engine.evaluate(case(product_name="Apple Watch Edition"))) == set()


def test_existing_accessory_rules_still_hold(engine):
    for name in ["Samsung Galaxy S24 case", "iPhone 18 Pro case"]:
        assert engine.evaluate(case(product_name=name)).matched_routes == []


@pytest.mark.parametrize("country", ["GB", "IN", "CA"])
def test_new_apple_warranties_are_us_only(engine, country):
    for name in ["MacBook Air M4", "Apple Watch Series 11", "AirPods Pro 3"]:
        res = engine.evaluate(case(product_name=name, purchase_country=country))
        assert apple_routes(res) == set()


def test_past_one_year_gives_no_route_and_the_ended_note(engine):
    res = engine.evaluate(case(product_name="MacBook Air M4", purchase_date="2025-08-01", failure_date="2026-07-20"))
    assert apple_routes(res) == set()
    assert any("Mac; U.S.)" in n and "ended on 2026-08-01" in n for n in res.notes)
    reason = next(r for r in res.no_match_reasons if r.code == "maker_warranty_ended")
    assert reason.message == "Apple's 1-year warranty ended on 1 Aug 2026, 1 year after the purchase date."


def test_other_brand_watch_is_not_an_apple_watch(engine):
    res = engine.evaluate(case(product_name="Galaxy Watch", product_brand="Samsung"))
    assert apple_routes(res) == set()


def test_new_records_follow_the_record_format(engine):
    fields = {"id", "category", "issuer_or_brand", "brand_short", "claim_action", "program_name", "coverage_summary",
              "coverage_region", "source_url", "verified_at", "countries", "warranty_years", "applicable_devices",
              "excluded_devices", "coverage", "remedy", "mandatory_conditions", "exclusions_and_caveats", "watch_phrases"}
    for rid in (MAC, WATCH, ACCESSORY):
        rec = engine.records[rid]
        assert fields <= set(rec), rid
        assert rec["verified_at"] == "2026-10-02"
        assert rec["countries"] == ["US"]
        assert rec["source_url"].startswith("https://www.apple.com/legal/warranty/products/")
        assert "{deadline}" in rec["claim_action"]
    assert not {"AirPods", "Apple Watch"} & set(engine.records[MAC]["applicable_devices"])
    assert "AirPods" not in engine.records[WATCH]["applicable_devices"]
    assert not {"Mac", "MacBook", "Apple Watch"} & set(engine.records[ACCESSORY]["applicable_devices"])
