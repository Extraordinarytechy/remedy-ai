"""
End-to-end check against the live site: evaluates every demo case through CloudFront, then
sends a generated receipt image through /api/extract (Amazon Textract + Amazon Bedrock), then
checks that a US receipt entered as a UK purchase is held for confirmation before a claim PDF.
Usage: python scripts/e2e_live.py https://<distribution>.cloudfront.net
"""
import base64
import io
import json
import sys
import urllib.error
import urllib.request

from PIL import Image, ImageDraw, ImageFont

BASE = sys.argv[1].rstrip("/")


def call(path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, json.loads(r.read())


def receipt_png() -> str:
    img = Image.new("RGB", (620, 760), "white")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 22)
        big = ImageFont.truetype("arialbd.ttf", 30)
    except OSError:
        font = big = ImageFont.load_default()
    lines = [
        (big, "BEST BUY #1024"),
        (font, "1000 Main Street, Springfield"),
        (font, "Date: 11/24/2023   Time: 10:42"),
        (font, ""),
        (font, "Apple iPhone 14 Plus 128GB     799.99"),
        (font, "Screen protector                19.99"),
        (font, ""),
        (font, "SUBTOTAL                       819.98"),
        (font, "TAX                             65.60"),
        (big, "TOTAL                  $885.58"),
        (font, ""),
        (font, "VISA DEBIT ************4092"),
        (font, "Thank you for shopping"),
    ]
    y = 30
    for f, text in lines:
        d.text((30, y), text, fill="black", font=f)
        y += 48
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode()


def defect_png() -> str:
    img = Image.new("RGB", (640, 480), (20, 20, 22))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((170, 40, 470, 440), radius=40, outline=(200, 200, 205), width=6)
    d.rectangle((190, 70, 450, 410), fill=(0, 0, 0))
    d.text((230, 230), "Camera: no preview", fill=(230, 230, 230))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode()


status, fixtures = call("/api/fixtures")
print("fixtures", status, list(fixtures))
for key, fx in fixtures.items():
    s, ev = call("/api/evaluate", fx)
    print(" ", key, s, ev["has_coverage"], [(r["route_id"], r["status"], bool(r.get("source_check"))) for r in ev["matched_routes"]], ev.get("evaluation_date"))

try:
    s, ex = call("/api/extract", {"receipt_base64": receipt_png(), "defect_image_base64": defect_png(), "product_hint": "iPhone 14 Plus"})
except urllib.error.HTTPError as e:
    if e.code != 429:
        raise
    # The per-visitor daily photo cap, reached by repeated runs from one IP. Nothing is faked:
    # the checks below that need a real Textract result are skipped.
    s, ex = 429, None
    print("extract 429 (daily photo limit reached):", json.loads(e.read()).get("detail"))
if ex:
    print("extract", s)
    print("  receipt:", json.dumps(ex["receipt_data"], indent=None)[:600])
    print("  visual :", json.dumps(ex["visual_evidence"], indent=None)[:600])


def post_status(path, payload):
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.headers.get("content-type")
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("content-type")


# The reviewer's case: the US receipt just read by Textract, entered as a UK purchase.
if ex:
    uk_case = {
        "case_id": "e2e_us_receipt_as_uk",
        "product_name": "Apple iPhone 14 Plus 128GB",
        "purchase_date": "2023-11-24",
        "failure_date": "2025-01-30",
        "purchase_country": "GB",
        "uk_region": "england_wales",
        "retailer": "Best Buy",
        "defect_description": "Screen flickers.",
        "receipt_data": ex["receipt_data"],
    }
    s, ev = call("/api/evaluate", uk_case)
    print("reviewer case", s, "pdf_allowed:", ev["pdf_allowed"], [(c["id"], c["severity"]) for c in ev["checks"]],
          [(r["route_id"], r["status"], r["deadline"]) for r in ev["matched_routes"]], ev["timeline"])
    print("  pdf before confirming:", post_status("/api/generate-package", {"case": uk_case}))
    print("  pdf after confirming :", post_status("/api/generate-package", {"case": {**uk_case, "confirmed_checks": ["country_currency"]}}))
else:
    print("reviewer case skipped: it needs a real Textract reading of the receipt")
print("  /api/intake removed  :", post_status("/api/intake", {}))

# Newest launch and newest Apple program.
for label, extra in (
    ("iPhone 18 Pro (new, US)", {"product_name": "Apple iPhone 18 Pro", "purchase_date": "2026-09-18", "failure_date": "2026-09-28",
                                 "defect_description": "Screen flickers"}),
    ("Mac mini M2 no power", {"product_name": "Apple Mac mini M2", "purchase_date": "2025-01-10", "failure_date": "2026-09-01",
                              "defect_description": "Will not turn on (no power)"}),
):
    s, ev = call("/api/evaluate", {"case_id": "e2e", "purchase_country": "US", **extra})
    print(label, s, [(r["route_id"], r["status"], r["deadline"]) for r in ev["matched_routes"]])
s, src = call("/api/sources")
idx = src.get("apple_index") or {}
print("gap alert: uncovered service programs", idx.get("uncovered_service_programs"),
      "| recall/exchange", len(idx.get("uncovered_recall_or_exchange_programs") or []))
print("E2E_DONE")
