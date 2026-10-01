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
USER_AGENT = "Mozilla/5.0 (compatible; RemedyAI-SourceWatch/1.0; +https://github.com/Extraordinarytechy/remedy-ai)"
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


def _norm_text(t: str) -> str:
    """Lower-case, straight quotes, single spaces: so typography changes don't count as changes."""
    t = t.lower().replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    return re.sub(r"\s+", " ", t).strip()


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
        # Long pages (e.g. Visa's benefits page) change for unrelated reasons. When a record names
        # the sentences it relies on, watch those lines only and report whether they are still there.
        phrases = [_norm_text(p) for p in rec.get("watch_phrases", [])]
        key_present = None
        watched = text
        if phrases and text:
            lines = [ln for ln in text.splitlines() if any(p in _norm_text(ln) for p in phrases)]
            key_present = all(any(p in _norm_text(ln) for ln in lines) for p in phrases)
            watched = "\n".join(lines) if lines else text
        digest = content_hash(watched) if watched else ""
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
        if phrases:
            status["key_text_present"] = key_present if text else None
        if rec.get("category") == "manufacturer_service_program" and "apple" in rec.get("issuer_or_brand", "").lower():
            status["listed_on_apple_index"] = (_normalise_title(rec["program_name"]) in listed) if titles else None
            # No titles means Apple's list couldn't be loaded or read: listing is unknown, so the
            # engine treats the program as unconfirmed rather than as still listed (fail closed).
            status["apple_index_ok"] = bool(titles)
        out[rid] = status
        out[rid]["_text"] = text  # kept in memory only, for snapshots

    # Gap alert: programs Apple lists that RemedyAI has no record for. Repair programs need a
    # person to verify and add a record; recall and exchange programs are reported separately.
    covered = {_normalise_title(r.get("program_name", "")) for r in records.values()}
    uncovered = [t for t in titles if _normalise_title(t) not in covered]
    out["apple_index"]["uncovered_service_programs"] = [t for t in uncovered if not is_recall_or_exchange(t)]
    out["apple_index"]["uncovered_recall_or_exchange_programs"] = [t for t in uncovered if is_recall_or_exchange(t)]
    return out


def is_recall_or_exchange(title: str) -> bool:
    return bool(re.search(r"\b(recall|exchange)\b", title, re.IGNORECASE))


def degraded_sources(result: Dict[str, Dict[str, Any]], previous: Dict[str, Dict[str, Any]]) -> List[str]:
    """
    Sources a person needs to look at after this run: page unreachable, the relied-on wording missing,
    text changed after the last human verification, Apple's list unreadable, or a program that was
    listed last time and isn't now. A record already known to be delisted is not reported again.
    """
    out: List[str] = []
    index = result.get("apple_index", {})
    if index and not index.get("titles"):
        out.append("apple_index: unreadable")
    for rid, st in result.items():
        if rid == "apple_index":
            continue
        if st.get("reachable") is False:
            out.append(f"{rid}: unreachable (HTTP {st.get('http_status')})")
        if st.get("key_text_present") is False:
            out.append(f"{rid}: relied-on wording missing")
        changed = (st.get("last_changed_at") or "")[:10]
        verified = (st.get("human_verified_at") or "")[:10]
        if changed and verified and changed > verified:
            out.append(f"{rid}: changed {changed}, verified {verified}")
        if st.get("listed_on_apple_index") is False and previous.get(rid, {}).get("listed_on_apple_index") is not False:
            out.append(f"{rid}: no longer on Apple's list")
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
    """Latest stored status per source id. Empty dict when running without AWS or when the
    status could not be read; `status_unavailable()` tells those two apart."""
    if not force and time.time() - _CACHE["at"] < CACHE_SECONDS:
        return _CACHE["status"]
    table = _table()
    status: Dict[str, Dict[str, Any]] = {}
    unavailable = False
    if table is not None:
        try:
            item = table.get_item(Key={"pk": "sourcewatch#latest"}).get("Item")
            if item and "status_json" in item:
                status = json.loads(item["status_json"])
            else:
                unavailable = True  # deployed, but no check has been stored yet
        except Exception as e:
            print(f"Source Watch status unavailable: {type(e).__name__}")
            unavailable = True
    # A failed read is cached briefly only, so it is retried soon.
    _CACHE.update(at=time.time() - (CACHE_SECONDS - 30 if unavailable else 0), status=status, unavailable=unavailable)
    return status


# Source Watch runs daily; a result older than this means a run was missed.
STALE_AFTER_HOURS = 36


def newest_check(status: Dict[str, Dict[str, Any]]) -> Optional[datetime]:
    times = []
    for st in status.values():
        try:
            times.append(datetime.fromisoformat(str(st.get("checked_at", ""))))
        except (TypeError, ValueError):
            continue
    return max(times) if times else None


def status_unavailable(now: Optional[datetime] = None) -> bool:
    """
    True when running in AWS and the latest Source Watch result can't be relied on: it could not be
    read, none has been stored yet, or the newest check is more than STALE_AFTER_HOURS old (the daily
    run stopped). Routes are then treated as unverified (fail closed), not as healthy.
    """
    if _CACHE.get("unavailable"):
        return True
    if not os.getenv("TABLE_NAME"):
        return False  # local development: no Source Watch at all
    newest = newest_check(_CACHE.get("status") or {})
    if newest is None:
        return True
    now = now or datetime.now(timezone.utc)
    return (now - newest).total_seconds() > STALE_AFTER_HOURS * 3600


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
    degraded = degraded_sources(result, previous)
    # CloudWatch embedded metric format: Lambda's log line becomes the RemedyAI/SourceWatch
    # DegradedSources metric (no extra API call or permission). An alarm emails the owner when > 0.
    print(json.dumps({
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [{"Namespace": "RemedyAI/SourceWatch", "Dimensions": [[]], "Metrics": [{"Name": "DegradedSources", "Unit": "Count"}]}],
        },
        "DegradedSources": len(degraded),
        "degraded": degraded,
    }))
    summary = {rid: {k: v for k, v in st.items() if k in ("http_status", "changed_this_run", "listed_on_apple_index")} for rid, st in result.items()}
    print(json.dumps({"source_watch": summary}))
    return summary
