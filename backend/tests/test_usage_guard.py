"""Per-visitor and global daily caps, with an in-memory stand-in for the DynamoDB table."""
import pytest
from botocore.exceptions import ClientError

from src.services import usage_guard


class FakeTable:
    def __init__(self):
        self.items = {}

    def get_item(self, Key, ConsistentRead=False):
        item = self.items.get(Key["pk"])
        return {"Item": dict(item)} if item else {}

    def put_item(self, Item, ConditionExpression=None):
        if Item["pk"] in self.items:
            raise ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem")
        self.items[Item["pk"]] = dict(Item)

    def update_item(self, Key, UpdateExpression, ConditionExpression, ExpressionAttributeValues):
        item = self.items.setdefault(Key["pk"], {"pk": Key["pk"]})
        if "calls" in item and item["calls"] > ExpressionAttributeValues[":max"]:
            raise ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "UpdateItem")
        item["calls"] = item.get("calls", 0) + ExpressionAttributeValues[":u"]


@pytest.fixture
def table(monkeypatch):
    t = FakeTable()
    monkeypatch.setenv("TABLE_NAME", "test")
    monkeypatch.setenv("DAILY_AI_CALL_LIMIT", "5")
    monkeypatch.setenv("PER_CLIENT_DAILY_LIMIT", "2")
    monkeypatch.setattr(usage_guard, "_table", lambda: t)
    return t


def test_per_client_cap_stops_one_visitor_but_not_others(table):
    usage_guard.consume(1, "203.0.113.7")
    usage_guard.consume(1, "203.0.113.7")
    with pytest.raises(usage_guard.LimitReached, match="You have reached"):
        usage_guard.consume(1, "203.0.113.7")
    usage_guard.consume(1, "198.51.100.2")  # another visitor still gets through


def test_global_cap_applies_across_visitors(table):
    for i in range(5):
        usage_guard.consume(1, f"198.51.100.{i}")
    with pytest.raises(usage_guard.LimitReached, match="whole site"):
        usage_guard.consume(1, "198.51.100.99")


def test_raw_ip_is_never_stored(table):
    usage_guard.consume(1, "203.0.113.7")
    dump = repr(table.items)
    assert "203.0.113.7" not in dump
    assert any(k.startswith("client#") for k in table.items)


def test_fails_closed_when_table_unavailable(monkeypatch):
    monkeypatch.setenv("TABLE_NAME", "test")

    def broken():
        raise RuntimeError("no table")

    monkeypatch.setattr(usage_guard, "_table", broken)
    with pytest.raises(usage_guard.LimitReached):
        usage_guard.consume(1, "203.0.113.7")
