from datetime import datetime, timezone
from src.escalation import format_reminder, should_remind


def test_should_remind_p0_overdue():
    thresholds = {"P0": 24, "P1": 48, "P2": None, "P3": None}
    now = datetime(2026, 4, 12, 12, 0, tzinfo=timezone.utc)
    waiting_since = datetime(2026, 4, 11, 10, 0, tzinfo=timezone.utc)  # 26h ago
    assert should_remind("P0", waiting_since, None, thresholds, now) is True


def test_should_not_remind_p0_not_yet_overdue():
    thresholds = {"P0": 24, "P1": 48, "P2": None, "P3": None}
    now = datetime(2026, 4, 12, 12, 0, tzinfo=timezone.utc)
    waiting_since = datetime(2026, 4, 12, 10, 0, tzinfo=timezone.utc)  # 2h ago
    assert should_remind("P0", waiting_since, None, thresholds, now) is False


def test_should_not_remind_p2_no_threshold():
    thresholds = {"P0": 24, "P1": 48, "P2": None, "P3": None}
    now = datetime(2026, 4, 12, 12, 0, tzinfo=timezone.utc)
    waiting_since = datetime(2026, 4, 1, 10, 0, tzinfo=timezone.utc)  # 11 days ago
    assert should_remind("P2", waiting_since, None, thresholds, now) is False


def test_should_not_remind_already_reminded_within_window():
    thresholds = {"P0": 24, "P1": 48, "P2": None, "P3": None}
    now = datetime(2026, 4, 12, 12, 0, tzinfo=timezone.utc)
    waiting_since = datetime(2026, 4, 10, 10, 0, tzinfo=timezone.utc)  # 50h ago
    last_reminded = datetime(2026, 4, 12, 6, 0, tzinfo=timezone.utc)  # 6h ago
    assert should_remind("P0", waiting_since, last_reminded, thresholds, now) is False


def test_should_remind_again_after_window():
    thresholds = {"P0": 24, "P1": 48, "P2": None, "P3": None}
    now = datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc)
    waiting_since = datetime(2026, 4, 10, 10, 0, tzinfo=timezone.utc)  # 74h ago
    last_reminded = datetime(2026, 4, 12, 10, 0, tzinfo=timezone.utc)  # 26h ago
    assert should_remind("P0", waiting_since, last_reminded, thresholds, now) is True


def test_should_not_remind_no_waiting_since():
    thresholds = {"P0": 24, "P1": 48, "P2": None, "P3": None}
    now = datetime(2026, 4, 12, 12, 0, tzinfo=timezone.utc)
    assert should_remind("P0", None, None, thresholds, now) is False


def test_format_reminder():
    text = format_reminder(
        chat_name="Logic Protocol Core",
        priority="P0",
        waiting_person="Marc",
        hours_overdue=26.5,
        preview="What about the vault params?",
    )
    assert "Logic Protocol Core" in text
    assert "P0" in text
    assert "Marc" in text
    assert "26h" in text
