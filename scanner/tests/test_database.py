import json
from datetime import datetime, timezone
from src.database import build_scan_insert, build_item_insert
from src.models import TriageItem, ScanResult, ScanStats, PriorityStats


def test_build_scan_insert():
    result = ScanResult(
        sources=["telegram"],
        dialogs_listed=80,
        dialogs_filtered=30,
        dialogs_classified=30,
        items=[],
        stats=ScanStats(total=0, by_priority=PriorityStats(P0=0, P1=0, P2=0, P3=0), by_status={}),
    )
    query, params = build_scan_insert(result)
    assert "INSERT INTO scans" in query
    assert params[0] == ["telegram"]
    assert params[1] == 80
    stats_json = json.loads(params[4])
    assert stats_json["total"] == 0


def test_build_item_insert():
    item = TriageItem(
        source="telegram", chat_name="Logic Protocol Core", chat_type="group",
        waiting_person="Marc", preview="What about the vault params?",
        context_summary="Marc asking about vault params", draft_reply="Hey Marc...",
        priority="P0", status="READ_NO_REPLY", tags=["deal blocker"],
        last_message_at=datetime(2026, 4, 7, 14, 0, tzinfo=timezone.utc),
        waiting_since=datetime(2026, 4, 7, 14, 0, tzinfo=timezone.utc),
        waiting_days=3, chat_id=-100123, message_id=42,
    )
    query, params = build_item_insert(item, "550e8400-e29b-41d4-a716-446655440000")
    assert "INSERT INTO triage_items" in query
    assert params[0] == "550e8400-e29b-41d4-a716-446655440000"
    assert params[1] == "telegram"
    assert params[2] == "Logic Protocol Core"
    assert params[4] == "Marc"
    assert params[8] == "P0"
    assert params[10] == ["deal blocker"]
