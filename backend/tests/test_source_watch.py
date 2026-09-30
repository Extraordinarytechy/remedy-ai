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


def test_text_change_after_human_check_adds_caveat():
    status = {"uk_cra_2015_goods": {"checked_at": "2026-10-05T06:00:00+00:00", "reachable": True, "last_changed_at": "2026-10-04T06:00:00+00:00", "human_verified_at": "2026-09-29"}}
    case = NormalizedCase(
        case_id="t", product_name="TV", purchase_date="2023-07-20", failure_date="2026-08-22",
        evaluation_date=AS_OF, purchase_country="GB", defect_description="Lines on screen",
    )
    route = EligibilityEngine().evaluate(case, source_status=status).matched_routes[0]
    assert route.status == "POTENTIALLY_ELIGIBLE"
    assert "changed on 2026-10-04" in route.provenance.exceptions[0]


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
