from datetime import datetime, timezone
from src.digest import format_digest
from src.models import TriageItem, ScanResult, ScanStats, PriorityStats


def make_item(priority: str, chat_name: str, waiting_person: str, waiting_days: int) -> TriageItem:
    return TriageItem(
        source="telegram",
        chat_name=chat_name,
        chat_type="group",
        waiting_person=waiting_person,
        preview="test message",
        priority=priority,
        status="READ_NO_REPLY",
        tags=[],
        waiting_days=waiting_days,
    )


def test_format_digest_basic():
    items = [
        make_item("P0", "StraitsX x Grab", "Marc", 3),
        make_item("P0", "TokenLogic Core", "Matt", 1),
        make_item("P1", "USDT0 Vault", "Team", 2),
        make_item("P2", "GHO LM", "Aura team", 1),
        make_item("P3", "Aave Governance", "Community", 0),
    ]
    result = ScanResult(
        sources=["telegram"],
        dialogs_listed=80,
        dialogs_filtered=35,
        dialogs_classified=35,
        items=items,
        stats=ScanStats(
            total=5,
            by_priority=PriorityStats(P0=2, P1=1, P2=1, P3=1),
            by_status={"READ_NO_REPLY": 5},
        ),
    )
    digest = format_digest(result)
    assert "P0" in digest
    assert "2 items" in digest or "2)" in digest
    assert "Marc" in digest
    assert "StraitsX" in digest
    assert "5 total items" in digest


def test_format_digest_empty():
    result = ScanResult(
        sources=["telegram"],
        dialogs_listed=80,
        dialogs_filtered=0,
        dialogs_classified=0,
        items=[],
        stats=ScanStats(
            total=0,
            by_priority=PriorityStats(P0=0, P1=0, P2=0, P3=0),
            by_status={},
        ),
    )
    digest = format_digest(result)
    assert "No items" in digest or "0 total" in digest


def test_format_digest_truncates_long_lists():
    items = [make_item("P0", f"Chat {i}", f"Person {i}", i) for i in range(10)]
    result = ScanResult(
        sources=["telegram"],
        dialogs_listed=80,
        dialogs_filtered=50,
        dialogs_classified=50,
        items=items,
        stats=ScanStats(
            total=10,
            by_priority=PriorityStats(P0=10, P1=0, P2=0, P3=0),
            by_status={"READ_NO_REPLY": 10},
        ),
    )
    digest = format_digest(result)
    assert "more" in digest.lower() or "+" in digest
