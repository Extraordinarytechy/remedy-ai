import base64
from datetime import date

import pytest
from fastapi.testclient import TestClient
from src.app import app, DEMO_FIXTURES

client = TestClient(app)
AS_OF = "2026-09-29"
PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082"
)


@pytest.fixture(autouse=True)
def server_clock(monkeypatch):
    """The API sets the claim date from its own clock; pin it so results don't depend on today."""
    import src.app as app_module

    monkeypatch.setattr(app_module, "today_utc", lambda: date.fromisoformat(AS_OF))


def fixture_as_of(key):
    return {**DEMO_FIXTURES[key], "evaluation_date": AS_OF}


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "apple_iphone14plus_rear_camera_2024" in data["knowledge_records"]


def test_fixtures_endpoint():
    fixtures = client.get("/api/fixtures").json()
    assert set(fixtures) == {
        "case1_apple_iphone14plus",
        "case2_visa_infinite_sony",
        "case3_uk_samsung_tv",
        "case4_unknown_unsupported",
    }


@pytest.mark.parametrize(
    "key, expected_route",
    [
        ("case1_apple_iphone14plus", "apple_iphone14plus_rear_camera_2024"),
        ("case2_visa_infinite_sony", "visa_infinite_extended_warranty_us"),
        ("case3_uk_samsung_tv", "uk_cra_2015_goods"),
        ("case4_unknown_unsupported", None),
    ],
)
def test_every_demo_fixture(key, expected_route):
    data = client.post("/api/evaluate", json=fixture_as_of(key)).json()
    if expected_route is None:
        assert data["has_coverage"] is False
        assert "NO VERIFIED COVERAGE FOUND" in data["unmatched_reason"]
    else:
        assert data["has_coverage"] is True
        assert [r["route_id"] for r in data["matched_routes"]] == [expected_route]


def test_intake_endpoint_removed():
    assert client.post("/api/intake", json={}).status_code in (404, 405)


def test_sources_endpoint_lists_every_record():
    data = client.get("/api/sources").json()
    ids = {s["id"] for s in data["sources"]}
    assert "apple_iphone14plus_rear_camera_2024" in ids
    assert all(s["source_url"].startswith("https://") for s in data["sources"])


def test_extract_rejects_invalid_image():
    assert client.post("/api/extract", json={"defect_image_base64": "not base64!!"}).status_code == 400


def test_extract_requires_an_image():
    assert client.post("/api/extract", json={}).status_code == 400


def test_free_text_length_is_limited():
    payload = {**fixture_as_of("case1_apple_iphone14plus"), "defect_description": "x" * 2001}
    assert client.post("/api/evaluate", json=payload).status_code == 422


def test_timeline_present_for_every_demo():
    for key in DEMO_FIXTURES:
        data = client.post("/api/evaluate", json=fixture_as_of(key)).json()
        tl = data["timeline"]
        fx = DEMO_FIXTURES[key]
        assert tl["purchase_date"] == fx["purchase_date"]
        assert tl["failure_date"] == fx["failure_date"]
        assert tl["claim_date"] == AS_OF
        for r in data["matched_routes"]:
            assert r["deadline"] and r["deadline_label"] and r["days_left"] >= 0


# ---------------------------------------------------------------------------
# Claim PDF: server-side evaluation only
# ---------------------------------------------------------------------------
def test_generate_package_ignores_forged_evaluation(monkeypatch):
    import src.app as app_module

    seen = {}
    real = app_module.pdf_service.generate_pdf

    def spy(case, evaluation):
        seen["evaluation"] = evaluation
        return real(case, evaluation)

    monkeypatch.setattr(app_module.pdf_service, "generate_pdf", spy)
    fixture = fixture_as_of("case4_unknown_unsupported")  # the engine finds no coverage
    forged = client.post("/api/evaluate", json=fixture_as_of("case1_apple_iphone14plus")).json()
    forged["case_id"] = fixture["case_id"]
    response = client.post("/api/generate-package", json={"case": fixture, "evaluation": forged})
    assert response.status_code == 200
    assert seen["evaluation"].has_coverage is False
    assert seen["evaluation"].matched_routes == []


def test_generate_package_blocked_until_hard_check_confirmed():
    us_receipt_as_uk = {
        **fixture_as_of("case3_uk_samsung_tv"),
        "receipt_data": {
            "store_name": "BEST BUY",
            "purchase_date": "2023-07-20",
            "currency_evidence": "$",
            "source": "textract",
        },
    }
    assert client.post("/api/generate-package", json={"case": us_receipt_as_uk}).status_code == 409
    confirmed = {**us_receipt_as_uk, "confirmed_checks": ["country_currency"]}
    assert client.post("/api/generate-package", json={"case": confirmed}).status_code == 200


def test_generate_package_filename_is_sanitised():
    fixture = {**fixture_as_of("case1_apple_iphone14plus"), "case_id": 'x"; evil=1\r\n.pdf'}
    response = client.post("/api/generate-package", json={"case": fixture})
    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'attachment; filename="RemedyAI_Claim_xevil1pdf.pdf"'


def test_demo_fixtures_are_labelled_as_sample_data():
    for fx in DEMO_FIXTURES.values():
        case = client.post("/api/evaluate", json={**fx, "evaluation_date": AS_OF})
        assert case.status_code == 200
    from src.models.schemas import NormalizedCase

    parsed = NormalizedCase(**DEMO_FIXTURES["case1_apple_iphone14plus"])
    assert parsed.receipt_data.source == "sample"
    assert parsed.visual_evidence.source == "sample"
    assert parsed.receipt_data.confidence_score is None


def test_generate_package_pdf():
    fixture = fixture_as_of("case1_apple_iphone14plus")
    evaluation = client.post("/api/evaluate", json=fixture).json()
    response = client.post("/api/generate-package", json={"case": fixture, "evaluation": evaluation})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    response = client.post("/api/generate-package", json={"case": fixture})  # evaluation is optional
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


# ---------------------------------------------------------------------------
# Only CloudFront may call the API in AWS
# ---------------------------------------------------------------------------
def test_direct_calls_refused_when_origin_secret_set(monkeypatch):
    monkeypatch.setenv("ORIGIN_VERIFY_SECRET", "s3cret-value")
    assert client.get("/health").status_code == 403
    assert client.get("/health", headers={"X-Origin-Verify": "wrong"}).status_code == 403
    assert client.get("/health", headers={"X-Origin-Verify": "s3cret-value"}).status_code == 200


def test_viewer_address_trusted_only_from_cloudfront(monkeypatch):
    from starlette.requests import Request
    from src.app import client_ip

    def make(headers):
        scope = {"type": "http", "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()], "client": ("198.51.100.7", 1234)}
        return Request(scope)

    monkeypatch.setenv("ORIGIN_VERIFY_SECRET", "s3cret-value")
    spoofed = make({"CloudFront-Viewer-Address": "203.0.113.9:443"})
    assert client_ip(spoofed) == "198.51.100.7"
    genuine = make({"CloudFront-Viewer-Address": "203.0.113.9:443", "X-Origin-Verify": "s3cret-value"})
    assert client_ip(genuine) == "203.0.113.9"


def test_no_cross_origin_access():
    response = client.get("/api/sources", headers={"Origin": "https://evil.example"})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


# ---------------------------------------------------------------------------
# Claim date is set by the server
# ---------------------------------------------------------------------------
def test_back_dated_claim_date_is_ignored():
    # The iPhone 12 program closed long before AS_OF; asking "as of 2023" must not reopen it.
    case = {
        "case_id": "t", "product_name": "Apple iPhone 12", "purchase_date": "2021-02-10",
        "failure_date": "2023-08-15", "evaluation_date": "2023-08-20", "purchase_country": "US",
        "defect_description": "No sound from the receiver during calls",
    }
    data = client.post("/api/evaluate", json=case).json()
    assert data["evaluation_date"] == AS_OF
    assert data["has_coverage"] is False
    assert client.post("/api/generate-package", json={"case": case}).status_code == 200  # a "nothing found" PDF


def test_visitor_calendar_date_one_day_either_side_is_kept():
    for sent in ("2026-09-28", "2026-09-30"):
        data = client.post("/api/evaluate", json={**fixture_as_of("case3_uk_samsung_tv"), "evaluation_date": sent}).json()
        assert data["evaluation_date"] == sent
    data = client.post("/api/evaluate", json={**fixture_as_of("case3_uk_samsung_tv"), "evaluation_date": None}).json()
    assert data["evaluation_date"] == AS_OF


def test_ambiguous_dates_are_rejected():
    data = client.post("/api/evaluate", json={**fixture_as_of("case3_uk_samsung_tv"), "purchase_date": "03/04/2024"}).json()
    assert data["has_coverage"] is False
    assert data["unmatched_reason"].startswith("INVALID INPUT")


# ---------------------------------------------------------------------------
# Upload and input bounds
# ---------------------------------------------------------------------------
def test_receipt_that_is_not_an_image_is_refused_before_any_call(monkeypatch):
    import src.app as app_module

    called = []
    monkeypatch.setattr(app_module.usage_guard, "consume", lambda *a, **k: called.append("consume"))
    monkeypatch.setattr(app_module.textract_service, "analyze_receipt_bytes", lambda b: called.append("textract"))
    pdf_as_receipt = base64.b64encode(b"%PDF-1.7 not an image").decode()
    response = client.post("/api/extract", json={"receipt_base64": pdf_as_receipt})
    assert response.status_code == 400
    assert "JPEG, PNG or WebP" in response.json()["detail"]
    assert called == []


def test_png_receipt_is_accepted(monkeypatch):
    import src.app as app_module
    from src.models.schemas import ReceiptData

    monkeypatch.setattr(app_module.textract_service, "analyze_receipt_bytes", lambda b: ReceiptData(source="unavailable"))
    response = client.post("/api/extract", json={"receipt_base64": base64.b64encode(PNG_BYTES).decode()})
    assert response.status_code == 200


def test_long_photo_observations_are_rejected():
    case = fixture_as_of("case1_apple_iphone14plus")
    case["visual_evidence"] = {**case["visual_evidence"], "visual_observations": ["x" * 301]}
    assert client.post("/api/evaluate", json=case).status_code == 422
    assert client.post("/api/generate-package", json={"case": case}).status_code == 422


def test_long_receipt_fields_are_rejected():
    case = fixture_as_of("case1_apple_iphone14plus")
    case["receipt_data"] = {**case["receipt_data"], "raw_fields": {"TOTAL": "9" * 501}}
    assert client.post("/api/evaluate", json=case).status_code == 422


def test_claim_pdf_is_counted(monkeypatch):
    import src.app as app_module

    seen = []
    monkeypatch.setattr(app_module.usage_guard, "consume", lambda units, ip, kind="photo": seen.append(kind))
    assert client.post("/api/generate-package", json={"case": fixture_as_of("case3_uk_samsung_tv")}).status_code == 200
    assert seen == ["pdf"]


def test_claim_pdf_limit_returns_429(monkeypatch):
    import src.app as app_module

    def refuse(*a, **k):
        raise app_module.usage_guard.LimitReached("You have reached today's limit of 30 claim PDFs.")

    monkeypatch.setattr(app_module.usage_guard, "consume", refuse)
    response = client.post("/api/generate-package", json={"case": fixture_as_of("case3_uk_samsung_tv")})
    assert response.status_code == 429


def test_cloudfront_request_without_viewer_address_has_no_visitor(monkeypatch):
    from starlette.requests import Request
    from src.app import client_ip

    monkeypatch.setenv("ORIGIN_VERIFY_SECRET", "s3cret-value")
    scope = {"type": "http", "headers": [(b"x-origin-verify", b"s3cret-value")], "client": ("198.51.100.7", 1234)}
    assert client_ip(Request(scope)) is None  # not the CloudFront edge address


# ---------------------------------------------------------------------------
# Options that must be checked first
# ---------------------------------------------------------------------------
def test_source_status_unavailable_blocks_the_claim_letter(monkeypatch):
    import src.app as app_module

    monkeypatch.setattr(app_module.source_watch, "load_status", lambda force=False: {})
    monkeypatch.setattr(app_module.source_watch, "status_unavailable", lambda: True)
    data = client.post("/api/evaluate", json=fixture_as_of("case3_uk_samsung_tv")).json()
    assert [r["status"] for r in data["matched_routes"]] == ["NEEDS_REVERIFICATION"]
    assert data["pdf_allowed"] is False
    assert client.post("/api/generate-package", json={"case": fixture_as_of("case3_uk_samsung_tv")}).status_code == 409
