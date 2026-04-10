from datetime import datetime, timezone
from src.database import should_reclassify, build_update_scanned_at


def test_should_reclassify_new_messages():
    last_scan_at = datetime(2026, 4, 10, 10, 0, tzinfo=timezone.utc)
    last_message_at = datetime(2026, 4, 10, 14, 0, tzinfo=timezone.utc)
    assert should_reclassify(last_message_at, last_scan_at, "open") is True


def test_should_not_reclassify_done_no_new_messages():
    last_scan_at = datetime(2026, 4, 10, 10, 0, tzinfo=timezone.utc)
    last_message_at = datetime(2026, 4, 10, 8, 0, tzinfo=timezone.utc)
    assert should_reclassify(last_message_at, last_scan_at, "done") is False


def test_should_not_reclassify_open_no_new_messages():
    last_scan_at = datetime(2026, 4, 10, 10, 0, tzinfo=timezone.utc)
    last_message_at = datetime(2026, 4, 10, 8, 0, tzinfo=timezone.utc)
    assert should_reclassify(last_message_at, last_scan_at, "open") is False


def test_should_reclassify_no_previous_item():
    assert should_reclassify(datetime.now(timezone.utc), None, None) is True


def test_build_update_scanned_at():
    query, params = build_update_scanned_at("item-uuid", "scan-uuid")
    assert "UPDATE triage_items" in query
    assert params[0] == "scan-uuid"
    assert params[1] == "item-uuid"
