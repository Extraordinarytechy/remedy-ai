"""
Masks account identifiers and email addresses in docs/evidence/*.log|*.txt|*.md|*.json (idempotent).

- 12-digit account IDs where they appear as account IDs (ARNs and "Account" fields), not inside
  request IDs, so every CloudTrail request ID stays checkable.
- IAM unique IDs (AIDA/AROA/AKIA/ASIA...), which encode the account number.
- Other bare 12-digit numbers (bucket names, URLs), except the last group of a UUID.
- Email addresses.
"""
import re
from pathlib import Path

ARN_ACCOUNT_RE = re.compile(r"(arn:aws[a-z-]*:[^:\s\"]*:[^:\s\"]*:)(\d{4})\d{4}(\d{4})")
FIELD_ACCOUNT_RE = re.compile(r"(\"Account\":\s*\")(\d{4})\d{4}(\d{4})")
UNIQUE_ID_RE = re.compile(r"\b(AIDA|AROA|AKIA|ASIA)[A-Z0-9]{12,}\b")
# Any other bare 12-digit number (bucket names, URLs), except the last group of a UUID request ID.
BARE_ACCOUNT_RE = re.compile(r"(?<![0-9a-fA-F]{4}-)(?<![\w])(\d{4})\d{4}(\d{4})(?![\w])|(?<=-)(?<![0-9a-fA-F]{4}-)(\d{4})\d{4}(\d{4})(?![\w])")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


def redact(t: str) -> str:
    t = ARN_ACCOUNT_RE.sub(r"\1\2****\3", t)
    t = FIELD_ACCOUNT_RE.sub(r"\1\2****\3", t)
    t = BARE_ACCOUNT_RE.sub(lambda m: f"{m.group(1) or m.group(3)}****{m.group(2) or m.group(4)}", t)
    t = UNIQUE_ID_RE.sub(r"\1****************", t)
    return EMAIL_RE.sub("<redacted-email>", t)


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent / "docs" / "evidence"
    for p in root.glob("*"):
        if p.suffix in {".log", ".txt", ".md", ".json"}:
            t = p.read_text(encoding="utf-8", errors="replace")
            n = redact(t)
            if n != t:
                p.write_text(n, encoding="utf-8")
                print("redacted", p.name)
    print("REDACT_DONE")
