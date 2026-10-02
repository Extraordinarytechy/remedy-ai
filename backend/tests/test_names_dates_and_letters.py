"""Apple product names with cases and bands, bare Samsung model names, denied symptoms, phone family
on-sale dates, plain date errors, the UK 30-day claim letter and each warranty's own remedy."""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from src.app import app
from src.engine.eligibility import EligibilityEngine
from src.engine.release_dates import RELEASE_DATES_FILE, load_family_floors, match_family
from src.models.schemas import NormalizedCase
from src.services import pdf_service
from src.services.pdf_service import ClaimPdfService

AS_OF = "2026-09-30"
MAC = "apple_one_year_limited_warranty_mac_us"
WATCH = "apple_one_year_limited_warranty_watch_us"
ACCESSORY = "apple_one_year_limited_warranty_accessories_us"
IOS = "apple_one_year_limited_warranty_ios_us"
APPLE_WARRANTIES = {MAC, WATCH, ACCESSORY, IOS}
PIXEL_DISPLAY = "google_pixel9pro_display_2025"

client = TestClient(app)


@pytest.fixture(scope="module")
def engine():
    return EligibilityEngine()


def case(**overrides):
    base = dict(
        case_id="t",
        product_name="Generic Product",
        purchase_date="2026-02-01",
        failure_date="2026-09-20",
        evaluation_date=AS_OF,
        purchase_country="US",
        defect_description="Stopped working.",
    )
    base.update(overrides)
    return NormalizedCase(**base)


def route_ids(res):
    return [r.route_id for r in res.matched_routes]


# ---------------------------------------------------------------------------
# Apple product names that include a case, band, stand or what comes in the box
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name, expected", [
    ("Apple Watch Series 10 Aluminum Case with Sport Band", WATCH),
    ("Apple Watch SE Midnight Aluminum Case with Sport Loop", WATCH),
    ("Apple Watch Ultra 2 Titanium Case", WATCH),
    ("AirPods Pro 2 with MagSafe Charging Case (USB-C)", ACCESSORY),
    ("AirPods (3rd generation) with Lightning Charging Case", ACCESSORY),
    ("AirPods Pro 3 charging case", ACCESSORY),
    ("AirPods Pro Charging Case", ACCESSORY),
    ("Pro Display XDR with Pro Stand", ACCESSORY),
    ("iMac 24-inch with Magic Keyboard and Magic Mouse", MAC),
    ("MacBook Pro 14 with Magic Keyboard", MAC),
    ("iPad Pro with Apple Pencil", IOS),
    ("Apple TV 4K with Siri Remote", IOS),
])
def test_full_apple_product_names_get_the_device_warranty(engine, name, expected):
    res = engine.evaluate(case(product_name=name))
    assert {r for r in route_ids(res) if r in APPLE_WARRANTIES} == {expected}
    assert len(res.matched_routes) == 1


@pytest.mark.parametrize("name", ["iPhone 17 case", "MacBook charger", "Apple TV app", "Apple Watch strap", "AirPods case",
                                  "iPhone 17 aluminum case", "Apple Watch Series 10 case"])
def test_accessories_are_still_not_the_device(engine, name):
    res = engine.evaluate(case(product_name=name))
    assert route_ids(res) == []
    assert res.no_match_reasons[0].code == "accessory"


def test_a_band_is_never_the_watch(engine):
    # "Apple Watch band" is an Apple accessory, so it gets the accessory warranty, not the watch's.
    assert route_ids(engine.evaluate(case(product_name="Apple Watch band"))) == [ACCESSORY]


# ---------------------------------------------------------------------------
# Bare Samsung model names
# ---------------------------------------------------------------------------
def test_dell_s24_monitor_is_not_a_galaxy_s24(engine):
    res = engine.evaluate(case(
        product_name="Dell S24 monitor", purchase_date="2023-03-01", failure_date="2026-09-01",
        purchase_country="GB", uk_region="england_wales", retailer="Currys",
    ))
    assert res.input_error is None
    assert route_ids(res) == ["uk_cra_2015_goods"]


@pytest.mark.parametrize("name, brand, purchase", [
    ("Galaxy S24", None, "2023-03-01"),
    ("Samsung S25 Ultra", None, "2024-03-01"),
    ("S24", "Samsung", "2023-03-01"),
])
def test_named_samsung_models_are_still_checked(engine, name, brand, purchase):
    res = engine.evaluate(case(product_name=name, product_brand=brand, purchase_date=purchase, failure_date="2026-09-01"))
    assert res.input_error == "before_release"


# ---------------------------------------------------------------------------
# Symptoms the description denies
# ---------------------------------------------------------------------------
def test_a_denied_symptom_does_not_match(engine):
    res = engine.evaluate(case(
        product_name="Pixel 9 Pro XL", purchase_date="2025-01-10", failure_date="2026-09-01",
        defect_description="The screen doesn't flicker and there is no vertical line, but the battery drains overnight",
    ))
    assert PIXEL_DISPLAY not in route_ids(res)


@pytest.mark.parametrize("rid, text", [
    ("apple_iphone14plus_rear_camera_2024", "Rear camera shows no preview"),
    ("apple_iphone12_no_sound_2021", "There is no sound on calls"),
    ("apple_mac_mini_2023_no_power_2025", "It has no power at all"),
    (PIXEL_DISPLAY, "There is a vertical line on the screen"),
])
def test_no_symptoms_still_match(engine, rid, text):
    assert engine._symptom_matches(case(defect_description=text), engine.records[rid])


def test_bare_no_denies_a_keyword(engine):
    record = engine.records[PIXEL_DISPLAY]
    assert not engine._symptom_matches(case(defect_description="There is no vertical line"), record)
    assert not engine._symptom_matches(case(defect_description="No flicker at all"), record)


# ---------------------------------------------------------------------------
# Phone family on-sale dates
# ---------------------------------------------------------------------------
def test_any_iphone_before_the_first_iphone_is_refused(engine):
    res = engine.evaluate(case(product_name="iPhone", purchase_date="2001-05-10", failure_date="2002-01-01"))
    assert res.input_error == "before_release"
    assert res.unmatched_reason == (
        "INVALID INPUT: The first iPhone went on sale in June 2007, so an iPhone can't have been bought in May 2001. "
        "Check the purchase date."
    )
    assert res.pdf_allowed is False


@pytest.mark.parametrize("name, purchase, first", [
    ("iPhone Air 2", "2001-01-01", "first iPhone"),
    ("Google Pixel 3", "2015-05-10", "first Pixel phone"),
    ("Galaxy S25 FE", "2009-05-10", "first Galaxy S"),
    ("Samsung Galaxy S", "2009-05-10", "first Galaxy S"),
])
def test_family_floor_applies_when_no_model_matches(engine, name, purchase, first):
    res = engine.evaluate(case(product_name=name, purchase_date=purchase, failure_date="2016-01-01"))
    assert res.input_error == "before_release"
    assert f"The {first} went on sale" in res.unmatched_reason


def test_most_specific_model_date_wins_over_the_family(engine):
    res = engine.evaluate(case(product_name="iPhone 17", purchase_date="2021-01-15", failure_date="2026-09-20"))
    assert "The iPhone 17 went on sale in September 2025" in res.unmatched_reason


@pytest.mark.parametrize("name, purchase", [
    ("iPhone 3G", "2007-06-10"),  # after the first iPhone: no model entry, so not blocked
    ("Pixel Watch", "2015-05-10"),
    ("Pixel Buds Pro", "2015-05-10"),
    ("Chromebook Pixel", "2013-05-10"),
    ("Samsung Smart TV", "2009-05-10"),
    ("Samsung Galaxy Tab S10", "2009-05-10"),
    ("Nokia 3310", "2001-05-10"),
    ("iPhone 17 case", "2001-05-10"),
])
def test_other_products_are_not_held_to_a_phone_family_date(engine, name, purchase):
    res = engine.evaluate(case(product_name=name, purchase_date=purchase, failure_date="2016-01-01"))
    assert res.input_error is None


def test_other_brand_is_not_held_to_a_family_date():
    assert match_family("Pixel 3", None, "Acme", load_family_floors()) is None


def test_family_floors_come_from_the_makers_pages():
    floors = {f["family"]: f for f in load_family_floors(RELEASE_DATES_FILE)}
    assert set(floors) == {"iPhone", "Pixel phone", "Galaxy S"}
    assert floors["iPhone"]["on_sale"] == "2007-06-29"
    assert floors["iPhone"]["source_url"].startswith("https://www.apple.com/newsroom/2007/06/")
    assert floors["Pixel phone"]["source_url"].startswith("https://blog.google/")
    assert floors["Galaxy S"]["source_url"].startswith("https://news.samsung.com/")


# ---------------------------------------------------------------------------
# Invalid input: plain messages and no claim PDF
# ---------------------------------------------------------------------------
def test_future_purchase_date_says_so(engine):
    res = engine.evaluate(case(purchase_date="2026-12-01", failure_date="2026-12-05"))
    assert res.input_error == "future_date"
    assert "The purchase date (2026-12-01) is in the future" in res.unmatched_reason


def test_future_failure_date_says_so(engine):
    res = engine.evaluate(case(failure_date="2026-12-05"))
    assert res.input_error == "future_date"
    assert "The failure date (2026-12-05) is in the future" in res.unmatched_reason


@pytest.mark.parametrize("bad", ["03/04/2025", "2026-02-30", "yesterday"])
def test_unreadable_date_has_no_parser_text(engine, bad):
    res = engine.evaluate(case(purchase_date=bad))
    assert res.input_error == "unreadable_date"
    assert res.unmatched_reason == (
        "INVALID INPUT: We couldn't read one of the dates. Check the purchase and failure dates."
    )
    assert res.next_steps == ["Check the purchase and failure dates."]
    assert "YYYY" not in res.unmatched_reason


@pytest.mark.parametrize("overrides", [
    dict(purchase_date="2026-05-01", failure_date="2026-01-01"),
    dict(purchase_date="1900-01-01"),
    dict(purchase_date="bad"),
    dict(product_name="iPhone 17", purchase_date="2021-01-15"),
])
def test_invalid_input_never_allows_a_claim_pdf(engine, overrides):
    res = engine.evaluate(case(**overrides))
    assert res.input_error is not None
    assert res.pdf_allowed is False


def test_generate_package_refuses_invalid_input(monkeypatch):
    import src.app as app_module

    monkeypatch.setattr(app_module, "today_utc", lambda: date.fromisoformat(AS_OF))
    body = case(product_name="iPhone 17", purchase_date="2021-01-15").model_dump()
    assert client.post("/api/evaluate", json=body).json()["pdf_allowed"] is False
    assert client.post("/api/generate-package", json={"case": body}).status_code == 409


# ---------------------------------------------------------------------------
# Claim letter wording
# ---------------------------------------------------------------------------
def letter_text(monkeypatch, c, engine):
    texts = []
    real = pdf_service.Paragraph

    def recording(text, *args, **kwargs):
        texts.append(str(text))
        return real(text, *args, **kwargs)

    monkeypatch.setattr(pdf_service, "Paragraph", recording)
    ClaimPdfService().generate_pdf(c, engine.evaluate(c))
    return next(t for t in texts if "I am writing about my" in t)


UK = dict(product_name="Kettle", purchase_country="GB", uk_region="england_wales", retailer="Currys",
          failure_date="2026-09-25", evaluation_date="2026-10-01")


def test_uk_letter_in_the_first_30_days_rejects_for_a_refund(engine, monkeypatch):
    c = case(**UK, purchase_date="2026-09-15")
    route = engine.evaluate(c).matched_routes[0]
    assert route.route_id == "uk_cra_2015_goods" and route.short_term_reject is True
    text = letter_text(monkeypatch, c, engine)
    assert "full refund (section 20)" in text and "section 20(15)" in text and "within 14 days" in text
    assert "section 23" not in text
    assert "tell me how to return the goods" in text


def test_uk_letter_after_30_days_asks_for_repair_under_section_23(engine, monkeypatch):
    c = case(**UK, purchase_date="2026-03-15")
    route = engine.evaluate(c).matched_routes[0]
    assert route.short_term_reject is False
    text = letter_text(monkeypatch, c, engine)
    assert "repair or replace them at no cost to me (section 23)" in text
    assert "section 20" not in text


def test_short_term_reject_defaults_to_false_for_other_routes(engine):
    res = engine.evaluate(case(product_name="iPhone 17"))
    assert res.matched_routes and all(r.short_term_reject is False for r in res.matched_routes)


# ---------------------------------------------------------------------------
# Each warranty's own remedy
# ---------------------------------------------------------------------------
def test_samsung_claim_names_repair_or_replacement_only(engine):
    res = engine.evaluate(case(product_name="Samsung Galaxy S25", product_brand="Samsung"))
    claim = next(r for r in res.matched_routes if r.route_id == "samsung_galaxy_limited_warranty_us").provenance.claim
    assert claim.endswith("Samsung will repair or replace it.")
    assert "refund" not in claim


@pytest.mark.parametrize("name, rid", [("iPhone 17", IOS), ("Pixel 10", "google_consumer_hardware_warranty_us_ca")])
def test_warranties_that_offer_a_refund_say_so(engine, name, rid):
    res = engine.evaluate(case(product_name=name))
    claim = next(r for r in res.matched_routes if r.route_id == rid).provenance.claim
    assert "will repair, replace or refund at its option" in claim
