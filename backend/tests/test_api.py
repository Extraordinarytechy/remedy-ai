import pytest
from fastapi.testclient import TestClient
from backend.src.app import app, DEMO_FIXTURES

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


def test_intake_without_image_records_no_visual_evidence():
    payload = {
        "product_name": "iPhone 14 Plus",
        "purchase_date": "2023-11-24",
        "failure_date": "2026-08-30",
        "defect_description": "Rear camera no preview",
    }
    data = client.post("/api/intake", json=payload).json()
    assert data["visual_evidence"] is None
    assert data["receipt_data"] is None


def test_generate_package_pdf():
    fixture = fixture_as_of("case1_apple_iphone14plus")
    evaluation = client.post("/api/evaluate", json=fixture).json()
    response = client.post("/api/generate-package", json={"case": fixture, "evaluation": evaluation})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
