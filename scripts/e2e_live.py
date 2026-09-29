"""
End-to-end check against the live site: evaluates every demo case through CloudFront, then
sends a generated receipt image through /api/extract (Amazon Textract + Amazon Bedrock).
Usage: python scripts/e2e_live.py https://<distribution>.cloudfront.net
"""
import base64
import io
import json
import sys
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

s, ex = call("/api/extract", {"receipt_base64": receipt_png(), "defect_image_base64": defect_png(), "product_hint": "iPhone 14 Plus"})
print("extract", s)
print("  receipt:", json.dumps(ex["receipt_data"], indent=None)[:600])
print("  visual :", json.dumps(ex["visual_evidence"], indent=None)[:600])
print("E2E_DONE")
