"""Samsung's U.S. phone warranty: a third brand added as a JSON record only."""
from src.engine.eligibility import EligibilityEngine, is_actionable
from src.models.schemas import NormalizedCase

RID = "samsung_galaxy_limited_warranty_us"


def case(**changes):
    body = dict(case_id="t", product_name="Samsung Galaxy Z Fold 7", product_brand="Samsung", purchase_date="2026-03-29",
                failure_date="2026-07-29", evaluation_date="2026-07-29", purchase_country="US",
                defect_description="Half of the inner display stopped working")
    body.update(changes)
    return NormalizedCase(**body)


def routes(c):
    return {r.route_id: r for r in EligibilityEngine().evaluate(c).matched_routes}


def test_galaxy_phone_in_first_year_matches_with_samsung_wording():
    r = routes(case())[RID]
    assert r.status == "POTENTIALLY_ELIGIBLE" and is_actionable(r)
    assert r.deadline == "2027-03-29" and r.deadline_label == "Samsung's warranty ends"
    assert "samsung.com/service" in r.recommended_action and "2027-03-29" in r.recommended_action
    assert "Apple" not in r.recommended_action + r.provenance.claim
    assert r.related_sources[0]["url"].startswith("https://www.samsung.com/us/support/legal/")


def test_galaxy_s_series_matches():
    assert RID in routes(case(product_name="Samsung Galaxy S25 Ultra"))


def test_outside_the_us_does_not_match():
    assert RID not in routes(case(purchase_country="IN"))
    assert RID not in routes(case(purchase_country="GB", uk_region="england_wales"))


def test_after_twelve_months_does_not_match():
    assert RID not in routes(case(purchase_date="2025-05-01", failure_date="2026-07-29"))


def test_other_galaxy_products_and_brands_do_not_match():
    for name in ("Samsung Galaxy Tab S10", "Samsung Galaxy Watch 8", "Samsung Galaxy Buds 3 Pro", "Samsung Galaxy Book4"):
        assert RID not in routes(case(product_name=name)), name
    assert RID not in routes(case(product_name="Samsung washer/dryer combo"))
    assert RID not in routes(case(product_name="Google Pixel 9", product_brand="Google"))
    assert RID not in routes(case(product_name="Samsung Galaxy S24 case"))
