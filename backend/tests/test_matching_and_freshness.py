"""Symptom matching that respects denials, and per-source freshness."""
import json

import pytest

from src.engine.eligibility import EligibilityEngine, is_actionable
from src.models.schemas import NormalizedCase


@pytest.fixture(scope="module")
def engine():
    return EligibilityEngine()


def pixel(desc, **kw):
    body = dict(case_id="t", product_name="Google Pixel 9 Pro", product_brand="Google", purchase_date="2024-10-05",
                failure_date="2026-09-20", evaluation_date="2026-10-01", purchase_country="US", defect_description=desc)
    body.update(kw)
    return NormalizedCase(**body)


def iphone(desc):
    return NormalizedCase(case_id="t", product_name="Apple iPhone 14 Plus", purchase_date="2024-03-15",
                          failure_date="2026-08-30", evaluation_date="2026-09-29", purchase_country="US",
                          defect_description=desc)


def program_ids(engine, case):
    return {r.route_id for r in engine.evaluate(case).matched_routes}


@pytest.mark.parametrize("desc", [
    "A green vertical line runs from the bottom to the top",
    "Screen keeps flickering when brightness is low",
    "The display flickers, and the phone gets hot",
    "Not working: vertical line down the display",
])
def test_stated_symptom_matches(engine, desc):
    assert "google_pixel9pro_display_2025" in program_ids(engine, pixel(desc))


@pytest.mark.parametrize("desc", [
    "It's not a vertical line, it's a dead pixel",
    "The screen doesn't flicker; the battery drains overnight",
    "There is no problem with the display flicker test, the speaker is broken",
    "Battery swelled without any flicker or lines",
    "The outline of the app icons is burned in",
])
def test_denied_or_unrelated_symptom_does_not_match(engine, desc):
    assert "google_pixel9pro_display_2025" not in program_ids(engine, pixel(desc))


def test_a_denial_in_one_clause_does_not_cancel_another(engine):
    desc = "The camera app isn't the issue, but a vertical line appeared on the screen"
    assert "google_pixel9pro_display_2025" in program_ids(engine, pixel(desc))


def test_no_preview_is_still_a_symptom(engine):
    # A bare "no" is part of the fault ("no preview"), not a denial.
    assert "apple_iphone14plus_rear_camera_2024" in program_ids(engine, iphone("Rear camera: no preview, just black"))
    assert "apple_iphone14plus_rear_camera_2024" not in program_ids(engine, iphone("No problem with the rear camera; the speaker crackles"))


# --- Freshness: a route whose source has no entry in the latest check is not trusted --------------
def test_route_without_a_source_check_entry_fails_closed(engine):
    status = {"uk_cra_2015_goods": {"checked_at": "2026-10-01T06:00:00+00:00", "reachable": True}}
    route = engine.evaluate(pixel("Vertical line on the display"), source_status=status).matched_routes[0]
    assert route.route_id == "google_pixel9pro_display_2025"
    assert route.status == "NEEDS_REVERIFICATION" and not is_actionable(route)
    assert "not been checked automatically yet" in route.provenance.exceptions[0]


def test_route_with_its_own_healthy_entry_stays_actionable(engine):
    status = {"google_pixel9pro_display_2025": {"checked_at": "2026-10-01T06:00:00+00:00", "reachable": True,
                                                "key_text_present": True, "human_verified_at": "2026-10-01"}}
    route = engine.evaluate(pixel("Vertical line on the display"), source_status=status).matched_routes[0]
    assert route.status == "ELIGIBLE_PENDING_INSPECTION" and is_actionable(route)


# --- Usage counts: numbers only, never case content -----------------------------------------------
def test_usage_metric_logs_counts_only(monkeypatch, capsys):
    from src import app as app_module

    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", "test")
    app_module.usage_metric(Checks=1, ChecksWithRoute=0)
    line = json.loads(capsys.readouterr().out.strip())
    assert line["Checks"] == 1 and line["ChecksWithRoute"] == 0
    assert set(line) == {"_aws", "Checks", "ChecksWithRoute"}
    assert line["_aws"]["CloudWatchMetrics"][0]["Namespace"] == "RemedyAI/Usage"


def test_usage_metric_is_off_outside_lambda(monkeypatch, capsys):
    from src import app as app_module

    monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)
    app_module.usage_metric(Checks=1)
    assert capsys.readouterr().out == ""
