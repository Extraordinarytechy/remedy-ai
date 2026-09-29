"""Masks 12-digit AWS account IDs in docs/evidence/*.log|*.txt|*.md|*.json (idempotent)."""
import re
from pathlib import Path

ACCOUNT_RE = re.compile(r"(?<!\d)(\d{4})\d{4}(\d{4})(?!\d)")
root = Path(__file__).resolve().parent.parent / "docs" / "evidence"
for p in root.glob("*"):
    if p.suffix in {".log", ".txt", ".md", ".json"}:
        t = p.read_text(encoding="utf-8", errors="replace")
        n = ACCOUNT_RE.sub(r"\1****\2", t)
        if n != t:
            p.write_text(n, encoding="utf-8")
            print("redacted", p.name)
print("REDACT_DONE")
