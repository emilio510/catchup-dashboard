import json
from datetime import datetime, timezone
from src.classifier import build_classification_prompt, parse_classification_response, SYSTEM_PROMPT
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


def test_build_prompt_includes_aliases_when_provided():
    conv = make_conversation("Test", [("Alice", "hi", False)])
    prompt = build_classification_prompt(
        [conv], "akgemilio", "I work at TokenLogic.",
        user_aliases=["Emile", "Em", "@AkgEmilio"],
    )
    assert "User aliases" in prompt
    assert "Emile" in prompt
    assert "@AkgEmilio" in prompt


def test_build_prompt_includes_topics_when_provided():
    conv = make_conversation("Test", [("Alice", "hi", False)])
    prompt = build_classification_prompt(
        [conv], "akgemilio", "I work at TokenLogic.",
        topics_owned=["Aave", "GHO", "USDT0"],
    )
    assert "Topics the user owns" in prompt
    assert "Aave" in prompt
    assert "USDT0" in prompt


def test_build_prompt_omits_aliases_section_when_empty():
    conv = make_conversation("Test", [("Alice", "hi", False)])
    prompt = build_classification_prompt(
        [conv], "akgemilio", "I work at TokenLogic.",
    )
    assert "User aliases" not in prompt


def test_build_prompt_omits_topics_section_when_empty():
    conv = make_conversation("Test", [("Alice", "hi", False)])
    prompt = build_classification_prompt(
        [conv], "akgemilio", "I work at TokenLogic.",
    )
    assert "Topics the user owns" not in prompt


ANCHOR = "--- YOUR LAST MESSAGE ABOVE ---"


def test_anchor_inserted_after_last_me_message():
    conv = make_conversation("Group", [
        ("Bob", "starting topic", False),
        ("Alice", "more context", False),
        ("Emile", "my take", True),
        ("Bob", "any thoughts on this?", False),
    ])
    prompt = build_classification_prompt([conv], "akgemilio", "")
    body = prompt.split("--- CHAT:")[1]
    assert ANCHOR in body
    me_idx = body.index("my take")
    anchor_idx = body.index(ANCHOR)
    later_idx = body.index("any thoughts on this?")
    assert me_idx < anchor_idx < later_idx


def test_anchor_omitted_when_no_me_message():
    conv = make_conversation("Group", [
        ("Bob", "starting topic", False),
        ("Alice", "more context", False),
    ])
    prompt = build_classification_prompt([conv], "akgemilio", "")
    assert ANCHOR not in prompt


def test_anchor_uses_most_recent_me_message_when_multiple():
    conv = make_conversation("Group", [
        ("Emile", "first take", True),
        ("Bob", "reply", False),
        ("Emile", "second take", True),
        ("Alice", "follow-up question", False),
    ])
    prompt = build_classification_prompt([conv], "akgemilio", "")
    body = prompt.split("--- CHAT:")[1]
    second_take_idx = body.index("second take")
    anchor_idx = body.index(ANCHOR)
    follow_up_idx = body.index("follow-up question")
    assert second_take_idx < anchor_idx < follow_up_idx
    # Anchor must NOT appear after the first me message — only after the last
    assert body.count(ANCHOR) == 1


def test_prompt_renders_reply_to_user_marker():
    me_msg = ChatMessage(
        sender_name="Emile", sender_id=100,
        text="should we ship the vault?",
        date=datetime(2026, 5, 7, 14, 0, tzinfo=timezone.utc),
        message_id=10, is_me=True,
    )
    reply_msg = ChatMessage(
        sender_name="Bob", sender_id=200,
        text="yes lgtm",
        date=datetime(2026, 5, 7, 14, 5, tzinfo=timezone.utc),
        message_id=11, is_me=False,
        reply_to_message_id=10,
    )
    conv = ConversationData(
        dialog=DialogInfo(chat_id=1, name="Group", is_channel=False, is_bot=False,
                          last_message_sender_is_me=False, last_message_date=reply_msg.date),
        messages=[me_msg, reply_msg],
        chat_type="group",
    )
    prompt = build_classification_prompt([conv], "akgemilio", "")
    assert '(↩ to YOU: "should we ship the vault?")' in prompt


def test_prompt_renders_reply_to_other_marker():
    alice_msg = ChatMessage(
        sender_name="Alice", sender_id=300,
        text="what's the timeline?",
        date=datetime(2026, 5, 7, 14, 0, tzinfo=timezone.utc),
        message_id=20, is_me=False,
    )
    bob_reply = ChatMessage(
        sender_name="Bob", sender_id=200,
        text="end of week",
        date=datetime(2026, 5, 7, 14, 5, tzinfo=timezone.utc),
        message_id=21, is_me=False,
        reply_to_message_id=20,
    )
    conv = ConversationData(
        dialog=DialogInfo(chat_id=1, name="Group", is_channel=False, is_bot=False,
                          last_message_sender_is_me=False, last_message_date=bob_reply.date),
        messages=[alice_msg, bob_reply],
        chat_type="group",
    )
    prompt = build_classification_prompt([conv], "akgemilio", "")
    assert '(↩ to "what\'s the timeline?")' in prompt
    assert "↩ to YOU" not in prompt


def test_prompt_renders_reply_outside_window_when_target_missing():
    bob_reply = ChatMessage(
        sender_name="Bob", sender_id=200,
        text="agreed",
        date=datetime(2026, 5, 7, 14, 5, tzinfo=timezone.utc),
        message_id=21, is_me=False,
        reply_to_message_id=999,  # not in conversation
    )
    conv = ConversationData(
        dialog=DialogInfo(chat_id=1, name="Group", is_channel=False, is_bot=False,
                          last_message_sender_is_me=False, last_message_date=bob_reply.date),
        messages=[bob_reply],
        chat_type="group",
    )
    prompt = build_classification_prompt([conv], "akgemilio", "")
    assert '(↩ to "msg outside window")' in prompt


def test_system_prompt_has_two_step_decision():
    assert "DECIDE IN THIS ORDER" in SYSTEM_PROMPT
    assert "Is the user being addressed" in SYSTEM_PROMPT


def test_system_prompt_has_strict_group_default():
    assert "GROUP CHATS" in SYSTEM_PROMPT
    assert "STRICT DEFAULT" in SYSTEM_PROMPT
    assert "addressed_to_user=false" in SYSTEM_PROMPT


def test_system_prompt_uses_lower_priority_default():
    assert "CHOOSE THE LOWER PRIORITY" in SYSTEM_PROMPT
    assert "ALWAYS choose the HIGHER" not in SYSTEM_PROMPT


def test_system_prompt_requires_addressed_to_user_field():
    assert "addressed_to_user" in SYSTEM_PROMPT
    assert "address_reason" in SYSTEM_PROMPT
