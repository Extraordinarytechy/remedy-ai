"""
Daily spend guard for the paid AI calls (Textract + Bedrock) behind a public, unauthenticated API.

One DynamoDB item per UTC day, incremented atomically with a conditional update. When the
counter reaches DAILY_AI_CALL_LIMIT the call is refused. If the counter cannot be read the
call is refused too (fail closed), because a broken counter would otherwise remove the ceiling.
Without TABLE_NAME (local development) the guard is disabled.
"""
import os
import time
from datetime import datetime, timezone


class LimitReached(Exception):
    pass


def consume(units: int = 1) -> None:
    name = os.getenv("TABLE_NAME")
    if not name or units <= 0:
        return
    limit = int(os.getenv("DAILY_AI_CALL_LIMIT", "100"))
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        import boto3
        from botocore.exceptions import ClientError

        boto3.resource("dynamodb").Table(name).update_item(
            Key={"pk": f"usage#{day}"},
            UpdateExpression="ADD calls :u SET expires_at = :ttl",
            ConditionExpression="attribute_not_exists(calls) OR calls <= :max",
            ExpressionAttributeValues={":u": units, ":max": limit - units, ":ttl": int(time.time()) + 3 * 86400},
        )
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            raise LimitReached(f"Daily limit of {limit} AI-assisted uploads reached. Try again tomorrow (UTC), or enter details manually.")
        raise LimitReached(f"Usage counter unavailable: {e.response.get('Error', {}).get('Code')}")
    except Exception as e:
        raise LimitReached(f"Usage counter unavailable: {type(e).__name__}")
