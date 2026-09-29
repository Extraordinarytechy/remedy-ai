"""Runs the Source Watch fetch + parse against the live sources (no AWS writes)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from src.services import source_watch as sw  # noqa: E402

idx = sw.fetch(sw.APPLE_INDEX_URL)
text = sw.visible_text(idx["html"])
print("apple index HTTP", idx["http_status"], "chars", len(text))
for t in sw.apple_index_titles(text):
    print("  title:", t)
for url in [
    "https://support.apple.com/iphone-14-plus-service-program-for-rear-camera-issue",
    "https://support.apple.com/en-in/iphone-12-and-iphone-12-pro-service-program-for-no-sound-issues",
    "https://www.visa.com/en-us/personal/cards/credit/visa-infinite",
    "https://www.gov.uk/accepting-returns-and-giving-refunds",
]:
    r = sw.fetch(url)
    body = sw.visible_text(r["html"])
    print(r["http_status"], len(body), sw.content_hash(body)[:12], url)
print("PROBE_DONE")
