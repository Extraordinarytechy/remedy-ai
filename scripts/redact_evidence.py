"""Masks 12-digit AWS account IDs and email addresses in docs/evidence/*.log|*.txt|*.md|*.json (idempotent)."""
import re
from pathlib import Path

ACCOUNT_RE = re.compile(r"(?<!\d)(\d{4})\d{4}(\d{4})(?!\d)")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
root = Path(__file__).resolve().parent.parent / "docs" / "evidence"
for p in root.glob("*"):
    if p.suffix in {".log", ".txt", ".md", ".json"}:
        t = p.read_text(encoding="utf-8", errors="replace")
        n = EMAIL_RE.sub("<redacted-email>", ACCOUNT_RE.sub(r"\1****\2", t))
        if n != t:
            p.write_text(n, encoding="utf-8")
            print("redacted", p.name)
print("REDACT_DONE")
