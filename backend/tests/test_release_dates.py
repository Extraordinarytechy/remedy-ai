"""Purchase dates that can't be right: more than 30 years old, or before the model went on sale."""
import json
import re
from datetime import date
from pathlib import Path

import pytest

from src.engine.eligibility import EligibilityEngine, MAX_PURCHASE_AGE_YEARS
from src.engine.release_dates import RELEASE_DATES_FILE, load_release_dates, match_model
from src.models.schemas import NormalizedCase

AS_OF = "2026-09-29"


@pytest.fixture(scope="module")
def engine():
    return EligibilityEngine()


def case(**overrides):
    base = dict(
        case_id="t",
        product_name="Generic Product",
        purchase_date="2026-01-10",
        failure_date="2026-09-01",
        evaluation_date=AS_OF,
        purchase_country="US",
        defect_description="Stopped working.",
    )
    base.update(overrides)
    return NormalizedCase(**base)


# ---------------------------------------------------------------------------
# Earliest allowed purchase date
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("purchase", ["1900-01-01", "0001-01-01"])
def test_ancient_purchase_dates_are_invalid_input(engine, purchase):
    res = engine.evaluate(case(product_name="iPhone 17", purchase_date=purchase))
    assert res.has_coverage is False
    assert res.matched_routes == []
    assert res.unmatched_reason.startswith("INVALID INPUT")
    assert res.input_error == "too_old"
    assert "more than 30 years" in res.unmatched_reason
    assert res.no_match_reasons == []


def test_exactly_thirty_years_is_accepted_one_day_more_is_not(engine):
    assert MAX_PURCHASE_AGE_YEARS == 30
    ok = engine.evaluate(case(purchase_date="1996-09-29"))
    assert ok.input_error is None
    assert not (ok.unmatched_reason or "").startswith("INVALID INPUT")
    too_old = engine.evaluate(case(purchase_date="1996-09-28"))
    assert too_old.input_error == "too_old"
    assert "on or after 1996-09-29" in too_old.unmatched_reason


def test_existing_date_rules_report_their_codes(engine):
    assert engine.evaluate(case(purchase_date="2026-05-01", failure_date="2026-01-01")).input_error == "failure_before_purchase"
    assert engine.evaluate(case(failure_date="2026-10-15")).input_error == "future_date"
    assert engine.evaluate(case(purchase_date="2026-02-30")).input_error == "unreadable_date"
    assert engine.evaluate(case(purchase_date="03/04/2024")).input_error == "unreadable_date"


# ---------------------------------------------------------------------------
# Model on-sale dates
# ---------------------------------------------------------------------------
def test_iphone_17_bought_in_2021_in_the_uk_is_refused(engine):
    res = engine.evaluate(case(
        product_name="iPhone 17", purchase_date="2021-01-15", failure_date="2026-09-20",
        purchase_country="GB", uk_region="england_wales", retailer="Currys",
    ))
    assert res.has_coverage is False
    assert res.matched_routes == []
    assert res.input_error == "before_release"
    assert res.unmatched_reason == (
        "INVALID INPUT: The iPhone 17 went on sale in September 2025, so it can't have been bought in "
        "January 2021. Check the purchase date."
    )
    assert res.next_steps == ["Check the purchase date and the model name."]


def test_most_specific_model_wins(engine):
    entries = engine.release_dates
    assert match_model("Apple iPhone 17 Pro Max", None, None, entries)["model"] == "iPhone 17 Pro Max"
    assert match_model("iPhone 17 Pro", None, None, entries)["model"] == "iPhone 17 Pro"
    assert match_model("iphone 17", None, None, entries)["model"] == "iPhone 17"
    assert match_model("Samsung Galaxy S24+", None, None, entries)["model"] == "Galaxy S24+"
    assert match_model("Galaxy Z Fold 7", None, None, entries)["model"] == "Galaxy Z Fold7"
    assert match_model("Pixel 9 Pro Fold", None, None, entries)["model"] == "Pixel 9 Pro Fold"
    assert match_model("Apple Mac mini (M2, 2023)", None, None, entries)["model"] == "Mac mini (2023)"


def test_purchase_in_the_announcement_month_is_accepted(engine):
    # iPhone 17 was announced on 9 Sep 2025 and pre-orders opened that week.
    res = engine.evaluate(case(product_name="iPhone 17", purchase_date="2025-09-01", failure_date="2026-09-01"))
    assert res.input_error is None
    blocked = engine.evaluate(case(product_name="iPhone 17", purchase_date="2025-08-31", failure_date="2026-09-01"))
    assert blocked.input_error == "before_release"


def test_month_only_on_sale_date_uses_the_month_before(engine):
    # Pixel 11: Google lists August 2026 only, so July 2026 is still accepted.
    assert engine.evaluate(case(product_name="Pixel 11", purchase_date="2026-07-01")).input_error is None
    res = engine.evaluate(case(product_name="Pixel 11", purchase_date="2026-06-30"))
    assert res.input_error == "before_release"
    assert "went on sale in August 2026" in res.unmatched_reason


@pytest.mark.parametrize("name", [
    "Galaxy S25 FE", "Galaxy S25 Edge", "Nokia 3310", "iPhone 17 case", "Mac mini M2 Pro",
    "iPhone Air 2", "Mac mini", "iPhone 18", "Apple Watch band",
])
def test_unknown_models_variants_and_accessories_are_never_blocked(engine, name):
    assert match_model(name, None, None, engine.release_dates) is None
    res = engine.evaluate(case(product_name=name, purchase_date="2001-01-01", failure_date="2002-01-01"))
    assert res.input_error is None


def test_a_suffix_is_part_of_the_model_name(engine):
    # "iPhone 16" never matches "iPhone 16e": each has its own entry and date.
    without_16e = [e for e in engine.release_dates if e["model"] != "iPhone 16e"]
    assert match_model("iPhone 16e", None, None, without_16e) is None
    assert match_model("iPhone 16e", None, None, engine.release_dates)["model"] == "iPhone 16e"


def test_other_brand_is_not_blocked(engine):
    res = engine.evaluate(case(product_name="iPhone 17", product_brand="Acme", purchase_date="2021-01-15"))
    assert res.input_error != "before_release"


def test_release_problem_runs_after_the_basic_date_rules(engine):
    # A failure date before the purchase date is reported as such, not as a release-date problem.
    res = engine.evaluate(case(product_name="iPhone 17", purchase_date="2021-05-01", failure_date="2021-01-01"))
    assert res.input_error == "failure_before_purchase"


# ---------------------------------------------------------------------------
# The data file itself
# ---------------------------------------------------------------------------
OFFICIAL = re.compile(r"^https://(www\.apple\.com/newsroom/|blog\.google/|support\.google\.com/|store\.google\.com/|"
                      r"news\.samsung\.com/|www\.samsung\.com/)")


def test_release_data_is_complete_and_from_official_pages():
    doc = json.loads(RELEASE_DATES_FILE.read_text(encoding="utf-8"))
    assert doc["verified_at"] == "2026-10-02"
    models = doc["models"]
    names = [m["model"] for m in models]
    assert len(names) == len(set(names))
    for m in models:
        assert OFFICIAL.match(m["source_url"]), m["model"]
        assert m["brand"] in {"Apple", "Google", "Samsung"}
        assert re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", m["on_sale"]), m["model"]
        if "announced" in m:
            date.fromisoformat(m["announced"])
            assert m["announced"][:7] <= m["on_sale"][:7], m["model"]
            if len(m["on_sale"]) == 10:
                assert m["announced"] <= m["on_sale"], m["model"]
    for required in ["iPhone 12", "iPhone 14 Plus", "iPhone 17", "iPhone 18 Pro Max", "Pixel 9 Pro Fold",
                     "Pixel 10", "Galaxy S24", "Galaxy S25 Ultra", "Galaxy S26", "Galaxy Z Fold6", "Galaxy Z Flip7",
                     "Mac mini (2023)"]:
        assert required in names


def test_release_data_lives_outside_the_knowledge_corpus():
    knowledge = (Path(__file__).resolve().parent.parent / "knowledge").resolve()
    assert knowledge not in RELEASE_DATES_FILE.resolve().parents
    assert load_release_dates(Path("does-not-exist.json")) == []
