import pytest
from fastapi.testclient import TestClient
from src.app import app, DEMO_FIXTURES

client = TestClient(app)
AS_OF = "2026-09-29"


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
