from src.engine.eligibility import EligibilityEngine
from src.models.schemas import NormalizedCase
from src.services import source_watch
from src.services.source_watch import apple_index_titles, visible_text, run_check

AS_OF = "2026-09-29"

APPLE_INDEX_HTML = """
<html><head><script>var x = "Fake Program";</script><style>.a{}</style></head>
<body>
<h1>Apple Service Programs</h1>
<ul>
  <li><a href="/a">Mac mini Service Program for No Power Issue</a> June 13, 2025</li>
  <li><a href="/b">iPhone 14 Plus Service Program for Rear Camera Issue</a> November 1, 2024</li>
  <li><a href="/c">15-inch MacBook Pro Battery Recall Program</a> June 20, 2019</li>
</ul>
</body></html>
"""


def iphone14plus_case():
    return NormalizedCase(
        case_id="t",
        product_name="iPhone 14 Plus",
        purchase_date="2023-11-24",
        failure_date="2026-08-30",
        evaluation_date=AS_OF,
        defect_description="Rear camera shows no preview",
    )


def test_visible_text_drops_scripts_and_tags():
    text = visible_text(APPLE_INDEX_HTML)
    assert "var x" not in text
    assert "<a" not in text
    assert "iPhone 14 Plus Service Program for Rear Camera Issue" in text


def test_apple_index_titles_extracts_program_names():
    titles = apple_index_titles(visible_text(APPLE_INDEX_HTML))
    assert "iPhone 14 Plus Service Program for Rear Camera Issue" in titles
    assert "Mac mini Service Program for No Power Issue" in titles
    assert all("Fake" not in t for t in titles)


def test_run_check_marks_delisted_program(monkeypatch):
    engine = EligibilityEngine()
    pages = {source_watch.APPLE_INDEX_URL: APPLE_INDEX_HTML}

    def fake_fetch(url, timeout=15):
        return {"http_status": 200, "html": pages.get(url, "<p>Program terms page</p>")}

    monkeypatch.setattr(source_watch, "fetch", fake_fetch)
    result = run_check(engine.records, previous={})
    assert result["apple_iphone14plus_rear_camera_2024"]["listed_on_apple_index"] is True
    assert result["apple_iphone12_no_sound_2021"]["listed_on_apple_index"] is False
    assert "listed_on_apple_index" not in result["uk_cra_2015_goods"]
    assert result["uk_cra_2015_goods"]["reachable"] is True


def test_run_check_detects_content_change(monkeypatch):
    engine = EligibilityEngine()
    monkeypatch.setattr(source_watch, "fetch", lambda url, timeout=15: {"http_status": 200, "html": "<p>version two</p>"})
    previous = {"uk_cra_2015_goods": {"content_hash": "old", "first_seen_at": "2026-09-01T00:00:00+00:00"}}
    result = run_check(engine.records, previous)
    assert result["uk_cra_2015_goods"]["changed_this_run"] is True
    assert result["uk_cra_2015_goods"]["first_seen_at"].startswith("2026-09-01")


def test_unreachable_source_downgrades_route():
    status = {"apple_iphone14plus_rear_camera_2024": {"checked_at": "2026-09-29T06:00:00+00:00", "http_status": 404, "reachable": False}}
    route = EligibilityEngine().evaluate(iphone14plus_case(), source_status=status).matched_routes[0]
    assert route.status == "NEEDS_REVERIFICATION"
    assert "could not load the source page" in route.provenance.exceptions[0]
    assert route.source_check["http_status"] == 404


def test_delisted_program_downgrades_route():
    status = {"apple_iphone14plus_rear_camera_2024": {"checked_at": "2026-09-29T06:00:00+00:00", "reachable": True, "listed_on_apple_index": False}}
    route = EligibilityEngine().evaluate(iphone14plus_case(), source_status=status).matched_routes[0]
    assert route.status == "NEEDS_REVERIFICATION"


def test_healthy_source_keeps_status_and_attaches_check():
    status = {"apple_iphone14plus_rear_camera_2024": {"checked_at": "2026-09-29T06:00:00+00:00", "reachable": True, "listed_on_apple_index": True}}
    route = EligibilityEngine().evaluate(iphone14plus_case(), source_status=status).matched_routes[0]
    assert route.status == "PENDING_SERIAL_VERIFICATION"
    assert route.source_check["listed_on_apple_index"] is True


UK_TV = dict(
    case_id="t", product_name="TV", purchase_date="2023-07-20", failure_date="2026-08-22",
    evaluation_date=AS_OF, purchase_country="GB", uk_region="england_wales", defect_description="Lines on screen",
)


def test_whole_page_change_after_human_check_fails_closed():
    # A record without watch phrases: any change to the page after verification blocks the route.
    status = {"uk_cra_2015_goods": {"checked_at": "2026-10-05T06:00:00+00:00", "reachable": True, "last_changed_at": "2026-10-04T06:00:00+00:00", "human_verified_at": "2026-09-29"}}
    evaluation = EligibilityEngine().evaluate(NormalizedCase(**UK_TV), source_status=status)
    route = evaluation.matched_routes[0]
    assert route.status == "NEEDS_REVERIFICATION"
    assert "changed on 2026-10-04" in route.provenance.exceptions[0]


def test_watched_wording_change_after_human_check_fails_closed(monkeypatch):
    # A phrase-scoped record whose watched lines changed (still present, but different) after verification.
    first = _visa_run(monkeypatch, f"<p>{VISA_SENTENCE}</p>", previous={})
    second = _visa_run(
        monkeypatch, f"<p>{VISA_SENTENCE} Claims must now be filed within 30 days.</p>",
        previous={"visa_infinite_extended_warranty_us": {"content_hash": first["content_hash"], "last_changed_at": ""}},
    )
    assert second["changed_this_run"] is True and second["key_text_present"] is True
    second.pop("_text", None)
    second["human_verified_at"] = "2026-09-30"
    second["last_changed_at"] = "2026-10-03T06:00:00+00:00"
    case = NormalizedCase(
        case_id="t", product_name="Sony headphones", purchase_date="2025-03-14", failure_date="2026-09-05",
        evaluation_date=AS_OF, payment_method="Visa Infinite", defect_description="Hinge cracked",
    )
    route = EligibilityEngine().evaluate(case, source_status={"visa_infinite_extended_warranty_us": second}).matched_routes[0]
    assert route.status == "NEEDS_REVERIFICATION"


def test_change_on_verification_day_is_not_flagged():
    status = {"uk_cra_2015_goods": {"checked_at": "2026-09-29T18:00:00+00:00", "reachable": True, "last_changed_at": "2026-09-29T17:00:00+00:00", "human_verified_at": "2026-09-29"}}
    route = EligibilityEngine().evaluate(NormalizedCase(**UK_TV), source_status=status).matched_routes[0]
    assert route.status != "NEEDS_REVERIFICATION"


def test_unreadable_apple_index_fails_closed(monkeypatch):
    engine = EligibilityEngine()
    pages = {source_watch.APPLE_INDEX_URL: "<p>Something went wrong.</p>"}
    monkeypatch.setattr(source_watch, "fetch", lambda url, timeout=15: {"http_status": 200, "html": pages.get(url, "<p>Program terms page</p>")})
    result = run_check(engine.records, previous={})
    st = result["apple_iphone14plus_rear_camera_2024"]
    assert st["listed_on_apple_index"] is None and st["apple_index_ok"] is False
    st.pop("_text", None)
    route = engine.evaluate(iphone14plus_case(), source_status={"apple_iphone14plus_rear_camera_2024": st}).matched_routes[0]
    assert route.status == "NEEDS_REVERIFICATION"
    assert "could not read Apple's service-program index" in route.provenance.exceptions[0]


def test_apple_index_http_error_fails_closed(monkeypatch):
    engine = EligibilityEngine()

    def fake_fetch(url, timeout=15):
        if url == source_watch.APPLE_INDEX_URL:
            return {"http_status": 503, "html": ""}
        return {"http_status": 200, "html": "<p>Program terms page</p>"}

    monkeypatch.setattr(source_watch, "fetch", fake_fetch)
    result = run_check(engine.records, previous={})
    assert result["apple_iphone14plus_rear_camera_2024"]["apple_index_ok"] is False
    assert "apple_index: unreadable" in source_watch.degraded_sources(result, previous={})


def test_degraded_sources_reports_what_needs_a_person():
    result = {
        "apple_index": {"titles": ["x Program"]},
        "a": {"reachable": False, "http_status": 404},
        "b": {"reachable": True, "key_text_present": False},
        "c": {"reachable": True, "last_changed_at": "2026-10-04T06:00:00+00:00", "human_verified_at": "2026-09-29"},
        "d": {"reachable": True, "listed_on_apple_index": False},
        "e": {"reachable": True, "listed_on_apple_index": False},
        "f": {"reachable": True, "listed_on_apple_index": True},
    }
    previous = {"d": {"listed_on_apple_index": True}, "e": {"listed_on_apple_index": False}}
    out = source_watch.degraded_sources(result, previous)
    assert out == [
        "a: unreachable (HTTP 404)",
        "b: relied-on wording missing",
        "c: changed 2026-10-04, verified 2026-09-29",
        "d: no longer on Apple's list",
    ]


def test_healthy_run_reports_nothing():
    result = {"apple_index": {"titles": ["x Program"]}, "a": {"reachable": True, "listed_on_apple_index": True}}
    assert source_watch.degraded_sources(result, previous={}) == []


def test_usage_guard_is_disabled_without_table():
    from src.services import usage_guard

    usage_guard.consume(2)  # no TABLE_NAME in tests: must not raise


def test_gap_alert_lists_programs_without_a_record(monkeypatch):
    engine = EligibilityEngine()
    html = APPLE_INDEX_HTML.replace(
        "</ul>", '<li><a href="/d">iPad Pro Service Program for Display Issue</a> October 1, 2026</li></ul>'
    )
    monkeypatch.setattr(
        source_watch, "fetch",
        lambda url, timeout=15: {"http_status": 200, "html": html if url == source_watch.APPLE_INDEX_URL else "<p>ok</p>"},
    )
    idx = run_check(engine.records, previous={})["apple_index"]
    assert idx["uncovered_service_programs"] == ["iPad Pro Service Program for Display Issue"]
    assert idx["uncovered_recall_or_exchange_programs"] == ["15-inch MacBook Pro Battery Recall Program"]
    # The Mac mini program now has a record, so it is not reported as a gap.
    assert "Mac mini Service Program for No Power Issue" not in idx["uncovered_service_programs"]


VISA_SENTENCE = (
    "When you use your covered Visa card for your eligible purchases Extended Warranty Protection will extend the term "
    "of your eligible manufacturer\u2019s U.S. warranty by 1 additional year on eligible warranties of 3 years or less."
)


def _visa_run(monkeypatch, body, previous):
    engine = EligibilityEngine()
    records = {"visa_infinite_extended_warranty_us": engine.records["visa_infinite_extended_warranty_us"]}
    monkeypatch.setattr(source_watch, "fetch", lambda url, timeout=15: {"http_status": 200, "html": body})
    return run_check(records, previous)["visa_infinite_extended_warranty_us"]


def test_watch_phrases_ignore_unrelated_page_changes(monkeypatch):
    first = _visa_run(monkeypatch, f"<p>Promo A</p><p>{VISA_SENTENCE}</p>", previous={})
    assert first["key_text_present"] is True
    second = _visa_run(
        monkeypatch, f"<p>Promo B, different today</p><p>{VISA_SENTENCE}</p>",
        previous={"visa_infinite_extended_warranty_us": {"content_hash": first["content_hash"]}},
    )
    assert second["changed_this_run"] is False


def test_missing_key_wording_downgrades_route(monkeypatch):
    st = _visa_run(monkeypatch, "<p>Extended Warranty Protection now adds 6 months.</p>", previous={})
    assert st["key_text_present"] is False
    st.pop("_text", None)
    case = NormalizedCase(
        case_id="t", product_name="Sony headphones", purchase_date="2025-03-14", failure_date="2026-09-05",
        evaluation_date=AS_OF, payment_method="Visa Infinite", defect_description="Hinge cracked",
    )
    route = EligibilityEngine().evaluate(case, source_status={"visa_infinite_extended_warranty_us": st}).matched_routes[0]
    assert route.status == "NEEDS_REVERIFICATION"
    assert "could not find the wording" in route.provenance.exceptions[0]


# --- A missed daily run is treated as "unverified", not as healthy ------------------------------
def _cached(monkeypatch, status, unavailable=False):
    from src.services import source_watch

    monkeypatch.setenv("TABLE_NAME", "test")
    monkeypatch.setitem(source_watch._CACHE, "status", status)
    monkeypatch.setitem(source_watch._CACHE, "unavailable", unavailable)
    return source_watch


def test_recent_check_is_trusted(monkeypatch):
    from datetime import datetime, timezone

    sw = _cached(monkeypatch, {"a": {"checked_at": "2026-10-01T06:00:00+00:00"}})
    assert sw.status_unavailable(now=datetime(2026, 10, 2, 6, 0, tzinfo=timezone.utc)) is False


def test_check_older_than_36_hours_is_stale(monkeypatch):
    from datetime import datetime, timezone

    sw = _cached(monkeypatch, {"a": {"checked_at": "2026-10-01T06:00:00+00:00"}})
    assert sw.status_unavailable(now=datetime(2026, 10, 2, 18, 30, tzinfo=timezone.utc)) is True


def test_no_stored_check_in_aws_is_unavailable(monkeypatch):
    sw = _cached(monkeypatch, {})
    assert sw.status_unavailable() is True


def test_local_development_has_no_source_watch(monkeypatch):
    from src.services import source_watch

    monkeypatch.delenv("TABLE_NAME", raising=False)
    monkeypatch.setitem(source_watch._CACHE, "status", {})
    monkeypatch.setitem(source_watch._CACHE, "unavailable", False)
    assert source_watch.status_unavailable() is False
