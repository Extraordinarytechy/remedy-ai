"""
Exports the AWS API calls made with the coding agent's IAM credentials, from CloudTrail
event history, to docs/evidence/. This is AWS's own record of what the agent did.

Usage (WSL/Linux, same credentials the agent uses):
    python3 scripts/export_cloudtrail.py --user aksilhoutte --since 2026-09-29
Writes docs/evidence/cloudtrail-<user>-<since>.json (redacted) and a summary .md.
"""
import argparse
import collections
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ACCOUNT_RE = re.compile(r"\b(\d{4})\d{4}(\d{4})\b")
IP_RE = re.compile(r"\b(\d{1,3})\.(\d{1,3})\.\d{1,3}\.\d{1,3}\b")


def redact(s: str) -> str:
    s = ACCOUNT_RE.sub(r"\1****\2", s)
    return IP_RE.sub(r"\1.\2.x.x", s)


def lookup(user: str, since: str):
    token, events = None, []
    while True:
        cmd = [
            "aws", "cloudtrail", "lookup-events",
            "--lookup-attributes", f"AttributeKey=Username,AttributeValue={user}",
            "--start-time", since, "--max-results", "50", "--output", "json",
        ]
        if token:
            cmd += ["--next-token", token]
        page = json.loads(subprocess.check_output(cmd))
        events.extend(page.get("Events", []))
        token = page.get("NextToken")
        if not token:
            return events


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True)
    ap.add_argument("--since", required=True, help="YYYY-MM-DD (UTC)")
    args = ap.parse_args()

    events = lookup(args.user, args.since)
    rows = []
    for e in events:
        detail = json.loads(e.get("CloudTrailEvent", "{}"))
        rows.append({
            # CloudTrail's own eventTime is UTC; the CLI's EventTime is rendered in the local timezone.
            "time": detail.get("eventTime") or str(e["EventTime"]),
            "event": e["EventName"],
            "source": e.get("EventSource"),
            "read_only": e.get("ReadOnly"),
            "user_agent": (detail.get("userAgent") or "")[:120],
            "request_id": detail.get("requestID"),
            "resources": [r.get("ResourceName") for r in e.get("Resources", [])][:3],
        })
    rows.sort(key=lambda r: r["time"])

    out = ROOT / "docs" / "evidence"
    out.mkdir(parents=True, exist_ok=True)
    stem = f"cloudtrail-{args.user}-{args.since}"
    (out / f"{stem}.json").write_text(redact(json.dumps(rows, indent=1)), encoding="utf-8")

    writes = [r for r in rows if r["read_only"] == "false"]
    by_service = collections.Counter(r["source"] for r in writes)
    def client(ua: str) -> str:
        u = ua.lower()
        if "sam-cli" in u or "aws-sam" in u:
            return "SAM CLI (run by the agent)"
        if "aws-cli" in u:
            return "AWS CLI (run by the agent)"
        if "cloudformation" in u:
            return "CloudFormation (stack deployed by the agent)"
        if "boto" in u or "botocore" in u:
            return "AWS SDK for Python (SAM CLI internals, run by the agent)"
        return f"other: {ua[:40] or 'no user agent'}"

    by_agent = collections.Counter(client(r["user_agent"]) for r in writes)
    # From 2026-10-01 the agent's deploy runs with AWS_SDK_UA_APP_ID=kiro-ide, so the AWS CLI and SAM CLI
    # add "app/kiro-ide" to each call's user agent. The client sets this tag; AWS records it as sent.
    tagged = [r for r in rows if "app/kiro-ide" in (r["user_agent"] or "").lower()]
    tagged_note = (
        f"- Calls whose user agent carries the `app/kiro-ide` tag (set by the agent's deploy script with "
        f"`AWS_SDK_UA_APP_ID`; a client-set value, recorded by AWS as sent): **{len(tagged)}**"
        + (f", first at `{min(r['time'] for r in tagged)}`, e.g. request {tagged[0]['request_id']}." if tagged else ".")
    )
    lines = [
        f"# CloudTrail: calls made with `{args.user}` since {args.since}",
        "",
        f"Exported {datetime.now(timezone.utc).isoformat(timespec='seconds')} from CloudTrail event history "
        f"(`aws cloudtrail lookup-events`). All times are UTC (CloudTrail `eventTime`). Account IDs and IPs redacted.",
        "",
        f"- Total events: **{len(rows)}**, of which **{len(writes)}** changed something (ReadOnly=false).",
        tagged_note,
        "",
        "| Client (from userAgent) | Mutating calls |",
        "| --- | ---: |",
        *[f"| {k} | {v} |" for k, v in by_agent.most_common()],
        "",
        "| Service | Mutating calls |",
        "| --- | ---: |",
        *[f"| {k} | {v} |" for k, v in by_service.most_common()],
        "",
        "First and last mutating calls:",
        "",
        *[f"- `{r['time']}` {r['event']} ({r['source']}) request {r['request_id']}" for r in (writes[:5] + writes[-5:])],
    ]
    (out / f"{stem}.md").write_text(redact("\n".join(lines)) + "\n", encoding="utf-8")
    print(f"EXPORTED {len(rows)} events ({len(writes)} mutating) -> docs/evidence/{stem}.*")


if __name__ == "__main__":
    main()
