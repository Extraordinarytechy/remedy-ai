"""
Source Watch: re-checks every primary source the engine relies on.

A scheduled Lambda (EventBridge, daily) fetches each knowledge record's source page and
Apple's service-program index, stores a text snapshot in S3 whenever the content changes,
and writes the current status to DynamoDB. The API reads that status so a route whose
source has disappeared is downgraded instead of being presented as a match.
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

APPLE_INDEX_URL = "https://support.apple.com/service-programs"
USER_AGENT = "Mozilla/5.0 (compatible; RemedyAI-SourceWatch/1.0; +https://github.com/)"
_CACHE: Dict[str, Any] = {"at": 0.0, "status": {}}
CACHE_SECONDS = 300


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fetch(url: str, timeout: int = 15) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return {"http_status": resp.status, "html": body}
    except urllib.error.HTTPError as e:
        return {"http_status": e.code, "html": ""}
    except Exception as e:  # network error, timeout
        return {"http_status": 0, "html": "", "error": str(e)[:200]}


def visible_text(page_html: str) -> str:
    """Strips scripts, styles and tags; keeps line breaks at block elements."""
    text = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", page_html)
    text = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h[1-6]|tr|section|article|a)>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    lines = [re.sub(r"[ \t\u00a0]+", " ", ln).strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def apple_index_titles(text: str) -> List[str]:
    """Program titles listed on Apple's service-program index, in page order, de-duplicated."""
    titles: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if 10 <= len(line) <= 140 and re.search(r"(Program|Programme)\b", line) and not line.lower().startswith("apple service program"):
            if line not in titles:
                titles.append(line)
    return titles


def _normalise_title(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", t.lower().replace("programme", "program")).strip()


def run_check(records: Dict[str, Dict[str, Any]], previous: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Pure check logic (no AWS calls). Returns the new status per source id plus an
    'apple_index' entry. `previous` is the last stored status, used to detect changes.
    """
    now = _now_iso()
    out: Dict[str, Dict[str, Any]] = {}

    index = fetch(APPLE_INDEX_URL)
    index_text = visible_text(index["html"]) if index["http_status"] == 200 else ""
    titles = apple_index_titles(index_text) if index_text else []
    prev_index = previous.get("apple_index", {})
    prev_titles = prev_index.get("titles", [])
    out["apple_index"] = {
        "url": APPLE_INDEX_URL,
        "checked_at": now,
        "http_status": index["http_status"],
        "titles": titles,
        "added_since_last_check": [t for t in titles if prev_titles and t not in prev_titles],
        "removed_since_last_check": [t for t in prev_titles if titles and t not in titles],
    }
    listed = {_normalise_title(t) for t in titles}

    for rid, rec in records.items():
        page = fetch(rec["source_url"])
        text = visible_text(page["html"]) if page["http_status"] == 200 else ""
        digest = content_hash(text) if text else ""
        prev = previous.get(rid, {})
        changed = bool(digest and prev.get("content_hash") and digest != prev.get("content_hash"))
        status: Dict[str, Any] = {
            "source_url": rec["source_url"],
            "checked_at": now,
            "http_status": page["http_status"],
            "reachable": page["http_status"] == 200,
            "content_hash": digest or prev.get("content_hash", ""),
            "first_seen_at": prev.get("first_seen_at") or (now if digest else ""),
            "last_changed_at": now if changed else prev.get("last_changed_at", ""),
            "changed_this_run": changed,
            "human_verified_at": rec.get("verified_at", ""),
        }
        if rec.get("category") == "manufacturer_service_program" and "apple" in rec.get("issuer_or_brand", "").lower():
            status["listed_on_apple_index"] = (_normalise_title(rec["program_name"]) in listed) if titles else None
        out[rid] = status
        out[rid]["_text"] = text  # kept in memory only, for snapshots
    return out


# ---------------------------------------------------------------------------
# AWS persistence (DynamoDB for status, S3 for snapshots)
# ---------------------------------------------------------------------------
def _table():
    name = os.getenv("TABLE_NAME")
    if not name:
        return None
    import boto3

    return boto3.resource("dynamodb").Table(name)


def load_status(force: bool = False) -> Dict[str, Dict[str, Any]]:
    """Latest stored status per source id. Empty dict when running without AWS."""
    if not force and time.time() - _CACHE["at"] < CACHE_SECONDS:
        return _CACHE["status"]
    table = _table()
    status: Dict[str, Dict[str, Any]] = {}
    if table is not None:
        try:
            item = table.get_item(Key={"pk": "sourcewatch#latest"}).get("Item")
            if item and "status_json" in item:
                status = json.loads(item["status_json"])
        except Exception as e:
            print(f"Source Watch status unavailable: {e}")
    _CACHE.update(at=time.time(), status=status)
    return status


def handler(event, context):  # EventBridge scheduled entry point
    from src.engine.eligibility import load_knowledge_records
    import boto3

    records = load_knowledge_records()
    previous = load_status(force=True)
    result = run_check(records, previous)

    bucket = os.getenv("SNAPSHOT_BUCKET")
    s3 = boto3.client("s3") if bucket else None
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for rid, st in result.items():
        text = st.pop("_text", "")
        is_new = text and not previous.get(rid, {}).get("content_hash")
        if s3 and text and (st.get("changed_this_run") or is_new):
            s3.put_object(
                Bucket=bucket,
                Key=f"snapshots/{rid}/{day}-{st['content_hash'][:12]}.txt",
                Body=text.encode("utf-8"),
                ContentType="text/plain; charset=utf-8",
            )

    table = _table()
    if table is not None:
        table.put_item(Item={"pk": "sourcewatch#latest", "status_json": json.dumps(result), "checked_at": _now_iso()})
    _CACHE.update(at=time.time(), status=result)
    summary = {rid: {k: v for k, v in st.items() if k in ("http_status", "changed_this_run", "listed_on_apple_index")} for rid, st in result.items()}
    print(json.dumps({"source_watch": summary}))
    return summary
