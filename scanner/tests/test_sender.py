from src.sender import build_fetch_pending_query, build_mark_sent_query, build_mark_failed_query


def test_build_fetch_pending_query():
    query = build_fetch_pending_query()
    assert "SELECT" in query
    assert "pending_replies" in query
    assert "'pending'" in query
    assert "'failed'" in query
    assert "retry_count < 3" in query
    assert "FOR UPDATE SKIP LOCKED" in query


def test_build_mark_sent_query():
    query, params = build_mark_sent_query("reply-uuid")
    assert "UPDATE pending_replies" in query
    assert "sent" in query
    assert params[0] == "reply-uuid"


def test_build_mark_failed_query():
    query, params = build_mark_failed_query("reply-uuid", "Connection error")
    assert "UPDATE pending_replies" in query
    assert "failed" in query
    assert params[0] == "Connection error"
    assert params[1] == "reply-uuid"
