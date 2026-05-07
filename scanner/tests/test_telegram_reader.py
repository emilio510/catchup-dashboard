from datetime import datetime, timezone, timedelta
from src.telegram_reader import (
    DialogInfo,
    ChatMessage,
    should_filter_dialog,
)
from src.config import ScannerConfig, ScanConfig, TelegramConfig


def make_config(**overrides) -> ScannerConfig:
    defaults = {
        "scan": ScanConfig(window_days=7, messages_per_chat=20, batch_size=5),
        "telegram": TelegramConfig(
            session_name="test",
            blacklist=["Spam Group", "Bot: PriceTracker"],
            bot_whitelist=[],
            api_id=12345,
            api_hash="testhash",
        ),
    }
    defaults.update(overrides)
    return ScannerConfig(**defaults)


def test_should_filter_blacklisted():
    config = make_config()
    dialog = DialogInfo(
        chat_id=1, name="Spam Group", is_channel=False, is_bot=False,
        last_message_sender_is_me=False, last_message_date=datetime.now(timezone.utc),
    )
    assert should_filter_dialog(dialog, config) is True


def test_should_filter_channel():
    config = make_config()
    dialog = DialogInfo(
        chat_id=2, name="Announcements", is_channel=True, is_bot=False,
        last_message_sender_is_me=False, last_message_date=datetime.now(timezone.utc),
    )
    assert should_filter_dialog(dialog, config) is True


def test_should_filter_bot():
    config = make_config()
    dialog = DialogInfo(
        chat_id=3, name="PriceBot", is_channel=False, is_bot=True,
        last_message_sender_is_me=False, last_message_date=datetime.now(timezone.utc),
    )
    assert should_filter_dialog(dialog, config) is True


def test_should_filter_i_spoke_last():
    config = make_config()
    dialog = DialogInfo(
        chat_id=4, name="Team Chat", is_channel=False, is_bot=False,
        last_message_sender_is_me=True, last_message_date=datetime.now(timezone.utc),
    )
    assert should_filter_dialog(dialog, config) is True


def test_should_not_filter_valid_chat():
    config = make_config()
    dialog = DialogInfo(
        chat_id=5, name="Logic Protocol Core", is_channel=False, is_bot=False,
        last_message_sender_is_me=False, last_message_date=datetime.now(timezone.utc),
    )
    assert should_filter_dialog(dialog, config) is False


def test_should_not_filter_old_chat_within_window():
    config = make_config()
    old_date = datetime.now(timezone.utc) - timedelta(days=10)
    dialog = DialogInfo(
        chat_id=6, name="Old Chat", is_channel=False, is_bot=False,
        last_message_sender_is_me=False, last_message_date=old_date,
    )
    # Old chats should NOT be filtered -- scan window only limits deep_read depth
    assert should_filter_dialog(dialog, config) is False


def test_chat_message_format():
    msg = ChatMessage(
        sender_name="Marc",
        sender_id=123,
        text="What about the vault params?",
        date=datetime(2026, 4, 7, 14, 30, tzinfo=timezone.utc),
        message_id=42,
        is_me=False,
    )
    formatted = msg.format()
    assert "Marc" in formatted
    assert "vault params" in formatted


def test_chat_message_carries_reply_to_message_id():
    msg_with_reply = ChatMessage(
        sender_name="Bob",
        sender_id=200,
        text="yeah I agree",
        date=datetime(2026, 5, 7, 12, 0, tzinfo=timezone.utc),
        message_id=42,
        is_me=False,
        reply_to_message_id=39,
    )
    assert msg_with_reply.reply_to_message_id == 39


def test_chat_message_reply_to_defaults_to_none():
    msg = ChatMessage(
        sender_name="Bob",
        sender_id=200,
        text="hello",
        date=datetime(2026, 5, 7, 12, 0, tzinfo=timezone.utc),
        message_id=1,
        is_me=False,
    )
    assert msg.reply_to_message_id is None


def test_format_renders_reply_to_user():
    msg = ChatMessage(
        sender_name="Bob",
        sender_id=200,
        text="agreed",
        date=datetime(2026, 5, 7, 12, 0, tzinfo=timezone.utc),
        message_id=42,
        is_me=False,
        reply_to_message_id=39,
    )
    rendered = msg.format(replied_text="should we ship the vault?", replied_is_me=True)
    assert '(↩ to YOU: "should we ship the vault?")' in rendered
    assert "agreed" in rendered


def test_format_renders_reply_to_other():
    msg = ChatMessage(
        sender_name="Bob",
        sender_id=200,
        text="agreed",
        date=datetime(2026, 5, 7, 12, 0, tzinfo=timezone.utc),
        message_id=42,
        is_me=False,
        reply_to_message_id=37,
    )
    rendered = msg.format(replied_text="alice's question text", replied_is_me=False)
    assert '(↩ to "alice\'s question text")' in rendered
    assert "↩ to YOU" not in rendered


def test_format_no_reply_marker_when_replied_text_none():
    msg = ChatMessage(
        sender_name="Bob",
        sender_id=200,
        text="hello",
        date=datetime(2026, 5, 7, 12, 0, tzinfo=timezone.utc),
        message_id=42,
        is_me=False,
    )
    rendered = msg.format()
    assert "↩" not in rendered


def test_format_truncates_replied_text_to_60_chars():
    long_text = "a" * 100
    msg = ChatMessage(
        sender_name="Bob",
        sender_id=200,
        text="ok",
        date=datetime(2026, 5, 7, 12, 0, tzinfo=timezone.utc),
        message_id=42,
        is_me=False,
        reply_to_message_id=37,
    )
    rendered = msg.format(replied_text=long_text, replied_is_me=False)
    assert "a" * 60 in rendered
    assert "a" * 61 not in rendered
