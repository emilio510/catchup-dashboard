import json
from datetime import datetime, timezone
from src.classifier import build_classification_prompt, parse_classification_response
from src.telegram_reader import DialogInfo, ChatMessage, ConversationData


def make_conversation(name: str, messages_data: list[tuple[str, str, bool]]) -> ConversationData:
    """Helper: (sender_name, text, is_me) tuples -> ConversationData."""
    messages = [
        ChatMessage(
            sender_name=sender,
            sender_id=100 if is_me else 200,
            text=text,
            date=datetime(2026, 4, 7, 14, i, tzinfo=timezone.utc),
            message_id=i,
            is_me=is_me,
        )
        for i, (sender, text, is_me) in enumerate(messages_data)
    ]
    return ConversationData(
        dialog=DialogInfo(
            chat_id=1, name=name, is_channel=False, is_bot=False,
            last_message_sender_is_me=False,
            last_message_date=messages[-1].date if messages else None,
        ),
        messages=messages,
        chat_type="group",
    )


def test_build_prompt_includes_chat_name():
    conv = make_conversation("Logic Protocol Core", [
        ("Marc", "What about the vault params?", False),
    ])
    prompt = build_classification_prompt([conv], "akgemilio", "I work at TokenLogic.")
    assert "Logic Protocol Core" in prompt
    assert "Marc" in prompt
    assert "vault params" in prompt


def test_build_prompt_includes_user_context():
    conv = make_conversation("Test", [("Alice", "Hello", False)])
    prompt = build_classification_prompt([conv], "akgemilio", "I work at TokenLogic.")
    assert "TokenLogic" in prompt


def test_parse_valid_response():
    response_json = json.dumps([
        {
            "chat_name": "Logic Protocol Core",
            "priority": "P0",
            "status": "READ_NO_REPLY",
            "waiting_person": "Marc",
            "waiting_since": "2026-04-07T14:00:00Z",
            "waiting_days": 3,
            "tags": ["deal blocker"],
            "context_summary": "Marc asking about vault parameters",
            "draft_reply": "Hey Marc, here are the params...",
            "preview": "What about the vault params?",
        }
    ])
    items = parse_classification_response(response_json, "telegram", "group", -100123, 42)
    assert len(items) == 1
    assert items[0].priority == "P0"
    assert items[0].waiting_person == "Marc"
    assert items[0].chat_id == -100123


def test_parse_handles_invalid_json():
    items = parse_classification_response("not json at all", "telegram", "group", 1, 1)
    assert items == []


def test_parse_handles_missing_fields():
    response_json = json.dumps([
        {
            "chat_name": "Test",
            "priority": "P2",
            "preview": "hello",
        }
    ])
    items = parse_classification_response(response_json, "telegram", "dm", 1, 1)
    assert len(items) == 1
    assert items[0].priority == "P2"
    assert items[0].status == "READ_NO_REPLY"


def test_build_prompt_includes_previous_context():
    conv = make_conversation("Logic Protocol Core", [
        ("Marc", "Any update on the vault?", False),
    ])
    previous_context = {
        "Logic Protocol Core": {
            "priority": "P0",
            "status": "READ_NO_REPLY",
            "user_status": "open",
            "preview": "What about the vault params?",
            "context_summary": "Marc asking about vault parameters",
        }
    }
    prompt = build_classification_prompt(
        [conv], "akgemilio", "I work at TokenLogic.",
        previous_context=previous_context,
    )
    assert "Previous classification" in prompt
    assert "P0" in prompt
    assert "What about the vault params?" in prompt


def test_build_prompt_includes_done_item_context():
    conv = make_conversation("Alice DM", [
        ("Alice", "Thanks!", False),
    ])
    previous_context = {
        "Alice DM": {
            "priority": "P1",
            "status": "READ_NO_REPLY",
            "user_status": "done",
            "preview": "Can you review this PR?",
            "context_summary": "Alice asked for PR review",
        }
    }
    prompt = build_classification_prompt(
        [conv], "akgemilio", "I work at TokenLogic.",
        previous_context=previous_context,
    )
    assert "done" in prompt.lower()
    assert "Alice asked for PR review" in prompt


def test_build_prompt_without_previous_context():
    conv = make_conversation("New Chat", [
        ("Bob", "Hey, got a minute?", False),
    ])
    prompt = build_classification_prompt([conv], "akgemilio", "I work at TokenLogic.")
    assert "Previous classification" not in prompt
