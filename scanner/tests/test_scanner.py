from src.scanner import Scanner
from src.models import TriageItem


def test_compute_stats():
    items = [
        TriageItem(source="telegram", chat_name="A", chat_type="dm", preview="x", priority="P0", status="READ_NO_REPLY"),
        TriageItem(source="telegram", chat_name="B", chat_type="group", preview="y", priority="P0", status="READ_NO_REPLY"),
        TriageItem(source="telegram", chat_name="C", chat_type="dm", preview="z", priority="P1", status="MONITORING"),
        TriageItem(source="telegram", chat_name="D", chat_type="group", preview="w", priority="P2", status="READ_NO_REPLY"),
    ]
    stats = Scanner._compute_stats(items)
    assert stats.total == 4
    assert stats.by_priority.P0 == 2
    assert stats.by_priority.P1 == 1
    assert stats.by_priority.P2 == 1
    assert stats.by_priority.P3 == 0
    assert stats.by_status["READ_NO_REPLY"] == 3
    assert stats.by_status["MONITORING"] == 1
