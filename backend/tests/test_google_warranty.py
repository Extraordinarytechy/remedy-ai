"""Google's warranty is a data-only record: no Google-specific code in the engine."""
from src.engine.eligibility import EligibilityEngine, is_actionable
from src.models.schemas import NormalizedCase, VisualDefectEvidence

RID = "google_consumer_hardware_warranty_us_ca"


def case(**changes):
    body = dict(
        case_id="t", product_name="Google Pixel 9", product_brand="Google", purchase_date="2026-03-01",
        failure_date="2026-09-15", evaluation_date="2026-10-01", purchase_country="US",
        defect_description="Phone restarts on its own several times a day",
    )
    body.update(changes)
    return NormalizedCase(**body)


def routes(c):
    return {r.route_id: r for r in EligibilityEngine().evaluate(c).matched_routes}


def test_pixel_in_first_year_matches_with_google_wording():
    r = routes(case())[RID]
    assert r.status == "POTENTIALLY_ELIGIBLE" and is_actionable(r)
    assert r.deadline == "2027-03-01"
    assert r.deadline_label == "Google's warranty ends"
    assert "g.co/warrantyclaim" in r.recommended_action and "2027-03-01" in r.recommended_action
    assert "Apple" not in r.recommended_action + r.provenance.claim + r.provenance.why_matched
    assert any("refurbished" in e for e in r.provenance.exceptions)
    assert r.related_sources[0]["url"].startswith("https://support.google.com/pixelphone/")


def test_pixel_bought_in_canada_matches():
    assert RID in routes(case(purchase_country="CA"))


def test_pixel_bought_in_the_uk_does_not_match():
    assert RID not in routes(case(purchase_country="GB", uk_region="england_wales"))


def test_pixel_after_one_year_does_not_match():
    assert RID not in routes(case(purchase_date="2025-03-01"))


def test_claim_date_after_warranty_explains_instead_of_matching():
    ev = EligibilityEngine().evaluate(case(purchase_date="2025-09-20", failure_date="2026-09-10", evaluation_date="2026-09-25"))
    assert RID not in {r.route_id for r in ev.matched_routes}
    ev = EligibilityEngine().evaluate(case(purchase_date="2025-09-01", failure_date="2026-08-20", evaluation_date="2026-09-25"))
    assert RID not in {r.route_id for r in ev.matched_routes}


def test_pixelbook_and_chromebook_pixel_are_excluded():
    assert RID not in routes(case(product_name="Google Pixelbook Go"))
    assert RID not in routes(case(product_name="Chromebook Pixel"))


def test_other_brands_do_not_match():
    assert RID not in routes(case(product_name="Samsung Galaxy S25", product_brand="Samsung"))
    assert RID not in routes(case(product_name="Apple iPhone 17", product_brand="Apple"))


def test_visible_damage_uses_googles_note():
    damaged = VisualDefectEvidence(visible_physical_damage=True, physical_damage_severity="screen_cracked", source="sample")
    r = routes(case(visual_evidence=damaged))[RID]
    assert r.provenance.exceptions[0].startswith("Visible physical damage") and "Google's warranty" in r.provenance.exceptions[0]


def test_apple_warranty_keeps_apple_wording():
    r = routes(case(product_name="Apple iPhone 17", product_brand="Apple"))["apple_one_year_limited_warranty_ios_us"]
    assert r.deadline_label == "Apple's warranty ends"
    assert "Apple Authorized Service Provider" in r.recommended_action
    assert r.related_sources[0]["url"] == "https://support.apple.com/102607"


# --- Pixel 9 Pro display program: a non-Apple repair program, also data-only -------------------
PROGRAM = "google_pixel9pro_display_2025"


def test_pixel9pro_vertical_line_in_year_two_matches_the_program():
    c = case(product_name="Google Pixel 9 Pro XL", purchase_date="2024-10-05", failure_date="2026-09-20",
             defect_description="A green vertical line runs from the bottom to the top of the screen")
    r = routes(c)[PROGRAM]
    assert r.status == "ELIGIBLE_PENDING_INSPECTION" and is_actionable(r)
    assert r.deadline == "2027-10-05"
    assert "Apple" not in r.recommended_action + r.summary + r.provenance.claim
    assert "Google walk-in center" in r.recommended_action
    assert RID not in routes(c)  # past the one-year warranty


def test_program_needs_the_listed_symptom():
    c = case(product_name="Google Pixel 9 Pro", purchase_date="2024-10-05", failure_date="2026-09-20",
             defect_description="Battery drains overnight")
    assert PROGRAM not in routes(c)


def test_program_excludes_other_pixels():
    for name in ("Google Pixel 9 Pro Fold", "Google Pixel 9", "Google Pixel 10 Pro"):
        c = case(product_name=name, purchase_date="2024-10-05", failure_date="2026-09-20",
                 defect_description="Vertical line on the display")
        assert PROGRAM not in routes(c), name


def test_program_window_closes_three_years_after_purchase():
    c = case(product_name="Google Pixel 9 Pro", purchase_date="2024-08-22", failure_date="2027-08-01",
             evaluation_date="2027-08-30", defect_description="Display flicker")
    assert PROGRAM not in routes(c)


def test_google_program_is_not_checked_against_apples_list():
    from src.services import source_watch
    from src.services.source_watch import run_check

    engine = EligibilityEngine()
    records = {PROGRAM: engine.records[PROGRAM]}
    import pytest

    mp = pytest.MonkeyPatch()
    mp.setattr(source_watch, "fetch", lambda url, timeout=15: {"http_status": 503, "html": ""} if url == source_watch.APPLE_INDEX_URL else {"http_status": 200, "html": "<p>Coverage lasts for 3 years after the original retail-purchase date.</p><p>Eligibility requires a vertical line on the display.</p>"})
    try:
        st = run_check(records, previous={})[PROGRAM]
    finally:
        mp.undo()
    assert "listed_on_apple_index" not in st and "apple_index_ok" not in st
    assert st["key_text_present"] is True
