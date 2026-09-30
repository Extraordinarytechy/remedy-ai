"""
Daily spend guard for the paid AI calls (Textract + Bedrock) behind a public, unauthenticated API.

Two counters per UTC day, each incremented atomically with a conditional update:
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


def consume(units: int = 1, client_ip: Optional[str] = None) -> None:
    if not os.getenv("TABLE_NAME") or units <= 0:
        return
    limit = int(os.getenv("DAILY_AI_CALL_LIMIT", "100"))
    per_client = int(os.getenv("PER_CLIENT_DAILY_LIMIT", "10"))
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        from botocore.exceptions import ClientError

        table = _table()
        stage = "client"
        try:
            if client_ip:
                _increment(table, f"client#{day}#{client_hash(_daily_key(table, day), client_ip)}", units, per_client)
            stage = "global"
            _increment(table, f"usage#{day}", units, limit)
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                if stage == "client":
                    raise LimitReached(
                        f"You have reached today's limit of {per_client} photo reads. "
                        "You can still type the details in yourself, or try again tomorrow (UTC)."
                    )
                raise LimitReached(
                    f"Today's limit of {limit} photo reads for the whole site has been reached. "
                    "You can still type the details in yourself, or try again tomorrow (UTC)."
                )
            raise LimitReached("Photo reading is unavailable right now. You can still type the details in yourself.")
    except LimitReached:
        raise
    except Exception:
        raise LimitReached("Photo reading is unavailable right now. You can still type the details in yourself.")
