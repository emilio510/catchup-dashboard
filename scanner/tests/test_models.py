from datetime import datetime, timezone
from src.models import TriageItem, ScanResult, ScanStats, PriorityStats


def test_triage_item_creation():
    item = TriageItem(
        source="telegram",
        chat_name="Logic Protocol Core",
        chat_type="group",
        waiting_person="Marc",
        preview="What are the vault yield parameters?",
        context_summary="Marc asking about XUSD vault config for Grab integration",
        draft_reply="Hey Marc, the target APY is 8% with a 3-day lockup...",
        priority="P0",
        status="READ_NO_REPLY",
        tags=["deal blocker", "waiting 3 days"],
        last_message_at=datetime(2026, 4, 7, 14, 0, tzinfo=timezone.utc),
        waiting_since=datetime(2026, 4, 7, 14, 0, tzinfo=timezone.utc),
        waiting_days=3,
        chat_id=-1001234567890,
        message_id=42,
    )
    assert item.source == "telegram"
    assert item.priority == "P0"
    assert item.waiting_days == 3


def test_triage_item_rejects_invalid_priority():
    import pytest
    with pytest.raises(Exception):
        TriageItem(
            source="telegram",
            chat_name="Test",
            chat_type="dm",
            preview="hello",
            priority="P5",
            status="READ_NO_REPLY",
        )


def test_triage_item_rejects_invalid_source():
    import pytest
    with pytest.raises(Exception):
        TriageItem(
            source="whatsapp",
            chat_name="Test",
            chat_type="dm",
            preview="hello",
            priority="P0",
            status="READ_NO_REPLY",
        )


def test_scan_stats():
    stats = ScanStats(
        total=34,
        by_priority=PriorityStats(P0=5, P1=8, P2=12, P3=9),
        by_status={"READ_NO_REPLY": 30, "MONITORING": 4},
    )
    assert stats.total == 34
    assert stats.by_priority.P0 == 5


def test_scan_result():
    result = ScanResult(
        sources=["telegram"],
        dialogs_listed=80,
        dialogs_filtered=35,
        dialogs_classified=35,
        items=[],
        stats=ScanStats(
            total=0,
            by_priority=PriorityStats(P0=0, P1=0, P2=0, P3=0),
            by_status={},
        ),
    )
    assert result.dialogs_listed == 80
    assert len(result.items) == 0


def test_scan_result_to_json():
    result = ScanResult(
        sources=["telegram"],
        dialogs_listed=10,
        dialogs_filtered=5,
        dialogs_classified=5,
        items=[],
        stats=ScanStats(
            total=0,
            by_priority=PriorityStats(P0=0, P1=0, P2=0, P3=0),
            by_status={},
        ),
    )
    json_str = result.model_dump_json()
    assert '"dialogs_listed": 10' in json_str or '"dialogs_listed":10' in json_str
