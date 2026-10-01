"""
Daily spend guard for a public, unauthenticated API: the paid AI calls (Textract + Bedrock) and
claim PDF builds are counted separately.

Two counters per kind and UTC day, each incremented atomically with a conditional update:
- a global counter (DAILY_AI_CALL_LIMIT), so total spend has a hard ceiling;
- a per-visitor counter (PER_CLIENT_DAILY_LIMIT), so one visitor cannot use up the day for everyone.

The per-visitor key is an HMAC of the visitor's IP address with a random key that is generated
per UTC day and stored in DynamoDB with a 2-day TTL. Raw IP addresses are never stored, and
once a day's key expires its hashes can no longer be linked to an address.

If a counter cannot be read the call is refused (fail closed), because a broken counter would
otherwise remove the ceiling. Without TABLE_NAME (local development) the guard is disabled.
"""
import hashlib
import hmac
import os
import secrets
import time
from datetime import datetime, timezone
from typing import Optional

TTL_SECONDS = 2 * 86400


class LimitReached(Exception):
    pass


def _table():
    import boto3

    return boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])


def _daily_key(table, day: str) -> bytes:
    """Random per-day HMAC key, created once per day (first writer wins)."""
    from botocore.exceptions import ClientError

    pk = f"salt#{day}"
    item = table.get_item(Key={"pk": pk}, ConsistentRead=True).get("Item")
    if item:
        return bytes.fromhex(item["value"])
    try:
        table.put_item(
            Item={"pk": pk, "value": secrets.token_hex(32), "expires_at": int(time.time()) + TTL_SECONDS},
            ConditionExpression="attribute_not_exists(pk)",
        )
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
            raise
    return bytes.fromhex(table.get_item(Key={"pk": pk}, ConsistentRead=True)["Item"]["value"])


def client_hash(key: bytes, client_ip: str) -> str:
    return hmac.new(key, client_ip.encode("utf-8"), hashlib.sha256).hexdigest()[:32]


def _increment(table, pk: str, units: int, limit: int) -> None:
    table.update_item(
        Key={"pk": pk},
        UpdateExpression="ADD calls :u SET expires_at = :ttl",
        ConditionExpression="attribute_not_exists(calls) OR calls <= :max",
        ExpressionAttributeValues={":u": units, ":max": limit - units, ":ttl": int(time.time()) + TTL_SECONDS},
    )


# What each counted action is called, its key prefixes and its limits (env var, default).
KINDS = {
    "photo": {
        "client_prefix": "client", "global_prefix": "usage", "noun": "photo reads",
        "global_env": ("DAILY_AI_CALL_LIMIT", "100"), "client_env": ("PER_CLIENT_DAILY_LIMIT", "10"),
        "fallback": "You can still type the details in yourself, or try again tomorrow (UTC).",
        "unavailable": "Photo reading is unavailable right now. You can still type the details in yourself.",
    },
    # Claim PDFs use no paid AI service, but each one is a Lambda run, so they are capped too.
    "pdf": {
        "client_prefix": "pdfclient", "global_prefix": "pdfusage", "noun": "claim PDFs",
        "global_env": ("DAILY_PDF_LIMIT", "2000"), "client_env": ("PER_CLIENT_DAILY_PDF_LIMIT", "30"),
        "fallback": "Please try again tomorrow (UTC).",
        "unavailable": "The claim PDF is unavailable right now. Please try again later.",
    },
}


def consume(units: int = 1, client_ip: Optional[str] = None, kind: str = "photo") -> None:
    if not os.getenv("TABLE_NAME") or units <= 0:
        return
    k = KINDS[kind]
    limit = int(os.getenv(*k["global_env"]))
    per_client = int(os.getenv(*k["client_env"]))
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        from botocore.exceptions import ClientError

        table = _table()
        stage = "client"
        try:
            if client_ip:
                visitor = client_hash(_daily_key(table, day), client_ip)
                _increment(table, f"{k['client_prefix']}#{day}#{visitor}", units, per_client)
            stage = "global"
            _increment(table, f"{k['global_prefix']}#{day}", units, limit)
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                if stage == "client":
                    raise LimitReached(f"You have reached today's limit of {per_client} {k['noun']}. {k['fallback']}")
                raise LimitReached(f"Today's limit of {limit} {k['noun']} for the whole site has been reached. {k['fallback']}")
            raise LimitReached(k["unavailable"])
    except LimitReached:
        raise
    except Exception:
        raise LimitReached(k["unavailable"])
