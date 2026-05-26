# Classifier Group-Chat Rework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop the Telegram classifier from over-firing on group chats by feeding it the signals it needs (aliases, reply chains, last-message anchor, owned topics) and replacing the system prompt with a strict-default group rule plus a deterministic post-processing enforcement gate.

**Architecture:** Approach A from the brainstorm. No new services, no DB migration, same single LLM call per batch. Two halves: (1) capture missing signals in `ChatMessage` and config, (2) rewrite `SYSTEM_PROMPT` with two-step decision (address → urgency) and a strict-default rule for groups, then enforce it deterministically in `classify_batch`.

**Tech Stack:** Python 3.12, pydantic for config, pytest with `asyncio_mode = "auto"`, anthropic SDK, Telethon for Telegram MTProto.

**Spec:** `docs/superpowers/specs/2026-05-07-classifier-group-chat-rework-design.md`

**Branch:** `rework/classifier-group-chats` (already created, spec already committed).

---

## File Structure

```
scanner/
  src/
    config.py             # MODIFY: extend ClassificationConfig with user_aliases + topics_owned
    telegram_reader.py    # MODIFY: add reply_to_message_id to ChatMessage; update format() signature; capture in deep_read
    classifier.py         # MODIFY: replace SYSTEM_PROMPT; update build_classification_prompt; add enforcement in classify_batch
  tests/
    test_telegram_reader.py  # MODIFY: add tests for ChatMessage field, format() variants, deep_read reply capture
    test_classifier.py       # MODIFY: add tests for aliases/topics injection, last-message anchor, reply chain rendering, enforcement
    test_config.py           # MODIFY: add test for new config fields loading
  config.yaml             # MODIFY: populate user_aliases and topics_owned lists
```

All test commands run from `~/Projects/catchup-dashboard/scanner/` directory.

---

## Task 1: Add `reply_to_message_id` field to `ChatMessage`

**Files:**
- Modify: `scanner/src/telegram_reader.py:25-37` (the `ChatMessage` dataclass)
- Test: `scanner/tests/test_telegram_reader.py` (append new tests)

- [ ] **Step 1.1: Write the failing test**

Append to `scanner/tests/test_telegram_reader.py`:

```python
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
```

- [ ] **Step 1.2: Run test to verify it fails**

```bash
cd ~/Projects/catchup-dashboard/scanner
pytest tests/test_telegram_reader.py::test_chat_message_carries_reply_to_message_id -v
```

Expected: FAIL with `TypeError: __init__() got an unexpected keyword argument 'reply_to_message_id'`.

- [ ] **Step 1.3: Add the field**

In `scanner/src/telegram_reader.py`, edit `ChatMessage`:

```python
@dataclass(frozen=True)
class ChatMessage:
    sender_name: str
    sender_id: int
    text: str
    date: datetime
    message_id: int
    is_me: bool
    reply_to_message_id: int | None = None

    def format(self) -> str:
        tag = " (me)" if self.is_me else ""
        ts = self.date.strftime("%Y-%m-%d %H:%M")
        return f"[{ts}] {self.sender_name}{tag}: {self.text}"
```

(Leave `format()` unchanged for now — Task 2 updates it.)

- [ ] **Step 1.4: Run tests to verify they pass**

```bash
pytest tests/test_telegram_reader.py -v
```

Expected: all green.

- [ ] **Step 1.5: Commit**

```bash
git add scanner/src/telegram_reader.py scanner/tests/test_telegram_reader.py
git commit -m "feat(scanner): add reply_to_message_id to ChatMessage"
```

---

## Task 2: Update `ChatMessage.format()` to render reply chains

**Files:**
- Modify: `scanner/src/telegram_reader.py` (the `format()` method on `ChatMessage`)
- Test: `scanner/tests/test_telegram_reader.py` (append four tests)

- [ ] **Step 2.1: Write the failing tests**

Append to `scanner/tests/test_telegram_reader.py`:

```python
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
```

- [ ] **Step 2.2: Run tests to verify they fail**

```bash
pytest tests/test_telegram_reader.py::test_format_renders_reply_to_user -v
```

Expected: FAIL with `TypeError: format() got an unexpected keyword argument 'replied_text'`.

- [ ] **Step 2.3: Update `format()`**

In `scanner/src/telegram_reader.py`, replace the `format` method on `ChatMessage`:

```python
    def format(self, replied_text: str | None = None, replied_is_me: bool = False) -> str:
        tag = " (me)" if self.is_me else ""
        ts = self.date.strftime("%Y-%m-%d %H:%M")
        prefix = f"[{ts}] {self.sender_name}{tag}"
        if replied_text:
            snippet = replied_text[:60].replace("\n", " ")
            if replied_is_me:
                prefix += f' (↩ to YOU: "{snippet}")'
            else:
                prefix += f' (↩ to "{snippet}")'
        return f"{prefix}: {self.text}"
```

- [ ] **Step 2.4: Run tests to verify they pass**

```bash
pytest tests/test_telegram_reader.py -v
```

Expected: all green. Pre-existing tests that call `format()` with no args still pass because both new parameters default to safe values.

- [ ] **Step 2.5: Commit**

```bash
git add scanner/src/telegram_reader.py scanner/tests/test_telegram_reader.py
git commit -m "feat(scanner): render reply chains in ChatMessage.format()"
```

---

## Task 3: Capture `reply_to_message_id` in `TelegramReader.deep_read`

**Files:**
- Modify: `scanner/src/telegram_reader.py:140-180` (the `deep_read` method)
- Test: `scanner/tests/test_telegram_reader.py` (append a test using a mocked Telethon client)

- [ ] **Step 3.1: Write the failing test**

Append to `scanner/tests/test_telegram_reader.py`:

```python
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from src.telegram_reader import TelegramReader


def _fake_telethon_message(*, msg_id: int, text: str, sender_id: int, date_min: int, reply_to_id: int | None):
    msg = MagicMock()
    msg.id = msg_id
    msg.text = text
    msg.sender = None  # forces sender_name="unknown" branch (we don't test that here)
    msg.sender_id = sender_id
    msg.date = datetime(2026, 5, 7, 12, date_min, tzinfo=timezone.utc)
    msg.reply_to = SimpleNamespace(reply_to_msg_id=reply_to_id) if reply_to_id is not None else None
    return msg


@pytest.mark.asyncio
async def test_deep_read_captures_reply_to_message_id():
    config = make_config()
    reader = TelegramReader(config)
    reader._me_id = 100

    fake_messages = [
        _fake_telethon_message(msg_id=1, text="original", sender_id=200, date_min=1, reply_to_id=None),
        _fake_telethon_message(msg_id=2, text="reply", sender_id=300, date_min=2, reply_to_id=1),
    ]

    async def fake_iter_messages(*args, **kwargs):
        for m in fake_messages:
            yield m

    fake_client = MagicMock()
    fake_client.iter_messages = fake_iter_messages
    fake_entity = SimpleNamespace()  # not a User, will become "group"
    fake_client.get_entity = AsyncMock(return_value=fake_entity)
    reader._client = fake_client

    dialog = DialogInfo(
        chat_id=999, name="Test Group", is_channel=False, is_bot=False,
        last_message_sender_is_me=False,
        last_message_date=datetime(2026, 5, 7, 12, 5, tzinfo=timezone.utc),
    )

    conv = await reader.deep_read(dialog)

    assert len(conv.messages) == 2
    assert conv.messages[0].reply_to_message_id is None
    assert conv.messages[1].reply_to_message_id == 1
```

- [ ] **Step 3.2: Run test to verify it fails**

```bash
pytest tests/test_telegram_reader.py::test_deep_read_captures_reply_to_message_id -v
```

Expected: FAIL — `reply_to_message_id` is `None` on both messages because `deep_read` does not yet read it.

- [ ] **Step 3.3: Update `deep_read` to capture reply IDs**

In `scanner/src/telegram_reader.py`, inside `deep_read`'s message loop, replace the `messages.append(...)` block with:

```python
            reply_to_id = None
            if msg.reply_to is not None:
                reply_to_id = getattr(msg.reply_to, "reply_to_msg_id", None)

            messages.append(
                ChatMessage(
                    sender_name=sender_name,
                    sender_id=sender_id,
                    text=msg.text,
                    date=msg.date,
                    message_id=msg.id,
                    is_me=sender_id == self._me_id,
                    reply_to_message_id=reply_to_id,
                )
            )
```

- [ ] **Step 3.4: Run tests to verify they pass**

```bash
pytest tests/test_telegram_reader.py -v
```

Expected: all green.

- [ ] **Step 3.5: Commit**

```bash
git add scanner/src/telegram_reader.py scanner/tests/test_telegram_reader.py
git commit -m "feat(scanner): capture reply_to_message_id in deep_read"
```

---

## Task 4: Extend `ClassificationConfig` with `user_aliases` and `topics_owned`

**Files:**
- Modify: `scanner/src/config.py:29-34` (the `ClassificationConfig` model)
- Test: `scanner/tests/test_config.py` (append two tests)

- [ ] **Step 4.1: Write the failing tests**

Append to `scanner/tests/test_config.py`:

```python
from src.config import ClassificationConfig


def test_classification_config_accepts_aliases_and_topics():
    config = ClassificationConfig(
        api_key="dummy",
        user_aliases=["Emile", "Em", "@AkgEmilio"],
        topics_owned=["Aave", "GHO"],
    )
    assert config.user_aliases == ["Emile", "Em", "@AkgEmilio"]
    assert config.topics_owned == ["Aave", "GHO"]


def test_classification_config_aliases_default_empty():
    config = ClassificationConfig(api_key="dummy")
    assert config.user_aliases == []
    assert config.topics_owned == []
```

- [ ] **Step 4.2: Run tests to verify they fail**

```bash
pytest tests/test_config.py::test_classification_config_accepts_aliases_and_topics -v
```

Expected: FAIL with pydantic `ValidationError` — extra fields not permitted.

- [ ] **Step 4.3: Add the fields**

In `scanner/src/config.py`, edit `ClassificationConfig`:

```python
class ClassificationConfig(BaseModel):
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    rate_limit_rpm: int = 30
    user_context: str = ""
    api_key: str = ""
    user_aliases: list[str] = Field(default_factory=list)
    topics_owned: list[str] = Field(default_factory=list)
```

- [ ] **Step 4.4: Run tests to verify they pass**

```bash
pytest tests/test_config.py -v
```

Expected: all green.

- [ ] **Step 4.5: Commit**

```bash
git add scanner/src/config.py scanner/tests/test_config.py
git commit -m "feat(scanner): add user_aliases + topics_owned to ClassificationConfig"
```

---

## Task 5: Inject aliases and topics into the prompt

**Files:**
- Modify: `scanner/src/classifier.py:56-106` (the `build_classification_prompt` function)
- Test: `scanner/tests/test_classifier.py` (append four tests)

- [ ] **Step 5.1: Write the failing tests**

Append to `scanner/tests/test_classifier.py`:

```python
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
```

- [ ] **Step 5.2: Run tests to verify they fail**

```bash
pytest tests/test_classifier.py::test_build_prompt_includes_aliases_when_provided -v
```

Expected: FAIL with `TypeError: build_classification_prompt() got an unexpected keyword argument 'user_aliases'`.

- [ ] **Step 5.3: Update `build_classification_prompt`**

In `scanner/src/classifier.py`, replace the entire `build_classification_prompt` function:

```python
def build_classification_prompt(
    conversations: list[ConversationData],
    my_display_name: str,
    user_context: str,
    calendar_context: str = "",
    previous_context: dict[str, dict] | None = None,
    notion_context: str = "",
    user_aliases: list[str] | None = None,
    topics_owned: list[str] | None = None,
) -> str:
    parts = [
        f"User context: {user_context}",
        f"User's display name in chats: {my_display_name}",
        f"Current time: {datetime.now(timezone.utc).isoformat()}",
        "",
    ]

    if user_aliases:
        parts.append("User aliases (any case-insensitive substring match counts as a mention):")
        for alias in user_aliases:
            parts.append(f"  - {alias}")
        parts.append("")

    if topics_owned:
        parts.append("Topics the user owns (decisions/actions on these topics likely require the user):")
        for topic in topics_owned:
            parts.append(f"  - {topic}")
        parts.append("")

    if calendar_context:
        parts.append(calendar_context)
        parts.append("")
        parts.append("IMPORTANT: If a conversation is related to an upcoming calendar event, boost its priority. Meeting prep should be at least P1.")
        parts.append("")

    if notion_context:
        parts.append(notion_context)
        parts.append("")

    parts += [
        "Conversations to classify:",
        "",
    ]

    for conv in conversations:
        parts.append(f"--- CHAT: {conv.dialog.name} (type: {conv.chat_type}) ---")

        prev = (previous_context or {}).get(conv.dialog.name)
        if prev:
            parts.append("Previous classification:")
            parts.append(f"  - Priority: {prev['priority']}")
            parts.append(f"  - Status: {prev['status']}")
            parts.append(f"  - User status: {prev['user_status']}")
            if prev.get("context_summary"):
                parts.append(f"  - Previous summary: \"{prev['context_summary']}\"")
            if prev.get("preview"):
                parts.append(f"  - Previous preview: \"{prev['preview']}\"")
            parts.append("")

        for msg in conv.messages:
            parts.append(msg.format())
        parts.append("")

    return "\n".join(parts)
```

(Reply chain rendering and last-message anchor are wired in Tasks 6 and 7. Don't add them here.)

- [ ] **Step 5.4: Run tests to verify they pass**

```bash
pytest tests/test_classifier.py -v
```

Expected: all green, including pre-existing tests (the new params default to `None`).

- [ ] **Step 5.5: Commit**

```bash
git add scanner/src/classifier.py scanner/tests/test_classifier.py
git commit -m "feat(scanner): inject user_aliases and topics_owned into classifier prompt"
```

---

## Task 6: Insert the "your last message" anchor

**Files:**
- Modify: `scanner/src/classifier.py` (the conversation rendering loop in `build_classification_prompt`)
- Test: `scanner/tests/test_classifier.py` (append three tests)

- [ ] **Step 6.1: Write the failing tests**

Append to `scanner/tests/test_classifier.py`:

```python
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
```

- [ ] **Step 6.2: Run tests to verify they fail**

```bash
pytest tests/test_classifier.py::test_anchor_inserted_after_last_me_message -v
```

Expected: FAIL — `ANCHOR not in body`.

- [ ] **Step 6.3: Insert the anchor**

In `scanner/src/classifier.py`, inside `build_classification_prompt`, replace the message loop:

```python
        for msg in conv.messages:
            parts.append(msg.format())
        parts.append("")
```

with:

```python
        last_me_index = -1
        for i, msg in enumerate(conv.messages):
            if msg.is_me:
                last_me_index = i

        for i, msg in enumerate(conv.messages):
            parts.append(msg.format())
            if i == last_me_index and last_me_index >= 0:
                parts.append("--- YOUR LAST MESSAGE ABOVE ---")
        parts.append("")
```

- [ ] **Step 6.4: Run tests to verify they pass**

```bash
pytest tests/test_classifier.py -v
```

Expected: all green.

- [ ] **Step 6.5: Commit**

```bash
git add scanner/src/classifier.py scanner/tests/test_classifier.py
git commit -m "feat(scanner): insert YOUR LAST MESSAGE ABOVE anchor in prompt"
```

---

## Task 7: Render reply chains inside the prompt

**Files:**
- Modify: `scanner/src/classifier.py` (the conversation rendering loop)
- Test: `scanner/tests/test_classifier.py` (append three tests)

- [ ] **Step 7.1: Write the failing tests**

Append to `scanner/tests/test_classifier.py`:

```python
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
```

- [ ] **Step 7.2: Run tests to verify they fail**

```bash
pytest tests/test_classifier.py::test_prompt_renders_reply_to_user_marker -v
```

Expected: FAIL — the prompt does not yet pass `replied_text` to `format()`.

- [ ] **Step 7.3: Wire the reply lookup into the rendering loop**

In `scanner/src/classifier.py`, replace the message loop you wrote in Task 6 with:

```python
        last_me_index = -1
        for i, msg in enumerate(conv.messages):
            if msg.is_me:
                last_me_index = i

        msg_by_id = {m.message_id: m for m in conv.messages}

        for i, msg in enumerate(conv.messages):
            replied_text: str | None = None
            replied_is_me = False
            if msg.reply_to_message_id is not None:
                target = msg_by_id.get(msg.reply_to_message_id)
                if target is not None:
                    replied_text = target.text
                    replied_is_me = target.is_me
                else:
                    replied_text = "msg outside window"
                    replied_is_me = False
            parts.append(msg.format(replied_text=replied_text, replied_is_me=replied_is_me))
            if i == last_me_index and last_me_index >= 0:
                parts.append("--- YOUR LAST MESSAGE ABOVE ---")
        parts.append("")
```

- [ ] **Step 7.4: Run tests to verify they pass**

```bash
pytest tests/test_classifier.py -v
```

Expected: all green.

- [ ] **Step 7.5: Commit**

```bash
git add scanner/src/classifier.py scanner/tests/test_classifier.py
git commit -m "feat(scanner): render Telegram reply chains in classifier prompt"
```

---

## Task 8: Replace `SYSTEM_PROMPT` with the strict-default version

**Files:**
- Modify: `scanner/src/classifier.py:17-53` (the `SYSTEM_PROMPT` constant)
- Test: `scanner/tests/test_classifier.py` (append four tests)

- [ ] **Step 8.1: Write the failing tests**

Append to `scanner/tests/test_classifier.py`:

```python
from src.classifier import SYSTEM_PROMPT


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
```

- [ ] **Step 8.2: Run tests to verify they fail**

```bash
pytest tests/test_classifier.py::test_system_prompt_has_two_step_decision -v
```

Expected: FAIL — current prompt has "When in doubt … HIGHER" and no two-step structure.

- [ ] **Step 8.3: Replace `SYSTEM_PROMPT`**

In `scanner/src/classifier.py`, replace the `SYSTEM_PROMPT` constant (currently around lines 17–53) with:

```python
SYSTEM_PROMPT = """\
You are a personal communication triage assistant.

DECIDE IN THIS ORDER:
1. Is the user being addressed by this conversation? (Most important in groups.)
2. If yes, what is the urgency?

GROUP CHATS (chat_type == "group") — STRICT DEFAULT:
The default is addressed_to_user=false, priority=P3, status=MONITORING.
Set addressed_to_user=true ONLY if at least one is true:
  (a) A message uses one of the user's aliases (case-insensitive substring match).
  (b) A message is a Telegram reply (rendered as "↩ to YOU") pointing to a message the user sent.
  (c) A direct question appears AFTER "--- YOUR LAST MESSAGE ABOVE ---" and
      either names a topic the user owns or follows naturally from what the
      user just said.
  (d) The conversation is asking for an action/decision on a topic the user
      owns (from the topics list provided).

DMs (chat_type == "dm"):
addressed_to_user=true by default, unless the conversation is clearly closed
(last message is "thanks", an emoji-only reply, or an acknowledgment).

PRIORITY (only when addressed_to_user=true):
- P0 Respond Today: actively blocked, deal-critical, multiple pings.
- P1 This Week: important deliverable, meeting prep, time-sensitive.
- P2 Respond: question or request, not urgent.
- P3 Monitor: FYI, no action needed.

WHEN UNCERTAIN, CHOOSE THE LOWER PRIORITY.
Better to miss a ping than spam the user.

STABILITY: don't downgrade a previous priority unless new messages clearly
resolve the conversation. Don't reopen "done" items on reactions/thanks/acks.

OUTPUT (JSON array, one entry per chat). Output ONLY the array.
{
  "chat_name": "...",
  "addressed_to_user": true|false,
  "address_reason": "alias_mention"|"reply_to_user"|"question_after_user"|"topic_owned"|"dm_default"|"not_addressed",
  "priority": "P0"|"P1"|"P2"|"P3",
  "status": "READ_NO_REPLY"|"NEW"|"MONITORING",
  "waiting_person": "..."|null,
  "waiting_since": "ISO 8601"|null,
  "waiting_days": int|null,
  "tags": [...],
  "context_summary": "1-2 sentences",
  "draft_reply": "..."|null,
  "preview": "200 chars"
}
"""
```

- [ ] **Step 8.4: Run tests to verify they pass**

```bash
pytest tests/test_classifier.py -v
```

Expected: all green.

- [ ] **Step 8.5: Commit**

```bash
git add scanner/src/classifier.py scanner/tests/test_classifier.py
git commit -m "feat(scanner): replace SYSTEM_PROMPT with strict-default group rule"
```

---

## Task 9: Add belt-and-suspenders enforcement in `classify_batch`

**Files:**
- Modify: `scanner/src/classifier.py` (the entry-construction loop in `Classifier.classify_batch`, plus the call to `build_classification_prompt`)
- Test: `scanner/tests/test_classifier.py` (append three tests using a mocked Anthropic client)

- [ ] **Step 9.1: Write the failing tests**

Append to `scanner/tests/test_classifier.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.classifier import Classifier
from src.config import ScannerConfig, ClassificationConfig, TelegramConfig


def _make_classifier_with_response(response_json: str) -> Classifier:
    config = ScannerConfig(
        classification=ClassificationConfig(api_key="dummy"),
        telegram=TelegramConfig(api_id=1, api_hash="x"),
    )
    classifier = Classifier(config)

    fake_response = MagicMock()
    fake_response.content = [MagicMock(type="text", text=response_json)]
    fake_response.stop_reason = "end_turn"

    classifier._client = MagicMock()
    classifier._client.messages = MagicMock()
    classifier._client.messages.create = AsyncMock(return_value=fake_response)
    return classifier


@pytest.mark.asyncio
async def test_enforcement_forces_p3_for_unaddressed_group():
    response = json.dumps([
        {
            "chat_name": "Big Group",
            "addressed_to_user": False,
            "address_reason": "not_addressed",
            "priority": "P0",  # model slipped — should be overridden
            "status": "READ_NO_REPLY",
            "preview": "...",
        }
    ])
    classifier = _make_classifier_with_response(response)
    conv = make_conversation("Big Group", [("Bob", "ambient chatter", False)])
    items = await classifier.classify_batch([conv], "akgemilio")
    assert len(items) == 1
    assert items[0].priority == "P3"
    assert items[0].status == "MONITORING"


@pytest.mark.asyncio
async def test_enforcement_does_not_override_dm_priority():
    response = json.dumps([
        {
            "chat_name": "Alice DM",
            "addressed_to_user": False,  # DM but model said false
            "address_reason": "not_addressed",
            "priority": "P1",
            "status": "READ_NO_REPLY",
            "preview": "...",
        }
    ])
    classifier = _make_classifier_with_response(response)
    dm_conv = ConversationData(
        dialog=DialogInfo(chat_id=42, name="Alice DM", is_channel=False, is_bot=False,
                          last_message_sender_is_me=False,
                          last_message_date=datetime(2026, 5, 7, 12, 0, tzinfo=timezone.utc)),
        messages=[ChatMessage(sender_name="Alice", sender_id=200, text="hey",
                              date=datetime(2026, 5, 7, 12, 0, tzinfo=timezone.utc),
                              message_id=1, is_me=False)],
        chat_type="dm",
    )
    items = await classifier.classify_batch([dm_conv], "akgemilio")
    assert items[0].priority == "P1"  # NOT overridden
    assert items[0].status == "READ_NO_REPLY"


@pytest.mark.asyncio
async def test_enforcement_does_not_override_addressed_group():
    response = json.dumps([
        {
            "chat_name": "Logic Protocol Core",
            "addressed_to_user": True,
            "address_reason": "alias_mention",
            "priority": "P1",
            "status": "READ_NO_REPLY",
            "preview": "...",
        }
    ])
    classifier = _make_classifier_with_response(response)
    conv = make_conversation("Logic Protocol Core", [("Marc", "Emile, can you look?", False)])
    items = await classifier.classify_batch([conv], "akgemilio")
    assert items[0].priority == "P1"  # NOT overridden — addressed=True
```

- [ ] **Step 9.2: Run tests to verify they fail**

```bash
pytest tests/test_classifier.py::test_enforcement_forces_p3_for_unaddressed_group -v
```

Expected: FAIL — priority remains "P0" because no enforcement exists yet.

- [ ] **Step 9.3: Wire the config into the prompt builder and add enforcement**

In `scanner/src/classifier.py`, update `Classifier.classify_batch`. First, find the call to `build_classification_prompt`:

```python
        prompt = build_classification_prompt(
            conversations,
            my_display_name,
            self._config.classification.user_context,
            calendar_context=self.calendar_context,
            previous_context=previous_context,
            notion_context=self.notion_context,
        )
```

Replace with:

```python
        prompt = build_classification_prompt(
            conversations,
            my_display_name,
            self._config.classification.user_context,
            calendar_context=self.calendar_context,
            previous_context=previous_context,
            notion_context=self.notion_context,
            user_aliases=self._config.classification.user_aliases,
            topics_owned=self._config.classification.topics_owned,
        )
```

Then find the entry-construction loop later in `classify_batch`. Inside the `for entry in data:` block, immediately after the lines that resolve `chat_name`, `conv`, `chat_id`, `chat_type`, `last_msg_id`, and before `last_msg_at = ...`, insert:

```python
                # Belt-and-suspenders enforcement: in group chats, if the model
                # says the user wasn't addressed, force the result to P3/MONITORING
                # regardless of what priority the model returned.
                if chat_type == "group" and not entry.get("addressed_to_user", False):
                    logger.info(
                        "Forcing P3/MONITORING for unaddressed group chat %r (model said priority=%s, address_reason=%s)",
                        chat_name,
                        entry.get("priority"),
                        entry.get("address_reason"),
                    )
                    entry["priority"] = "P3"
                    entry["status"] = "MONITORING"
```

- [ ] **Step 9.4: Run tests to verify they pass**

```bash
pytest tests/test_classifier.py -v
```

Expected: all green.

- [ ] **Step 9.5: Run the full scanner test suite**

```bash
pytest -v
```

Expected: all green. Confirms no regression in dedup, sender, escalation, calendar, notion, integration tests.

- [ ] **Step 9.6: Commit**

```bash
git add scanner/src/classifier.py scanner/tests/test_classifier.py
git commit -m "feat(scanner): enforce P3/MONITORING for unaddressed group chats"
```

---

## Task 10: Populate `config.yaml` with aliases and topics

**Files:**
- Modify: `scanner/config.yaml`

- [ ] **Step 10.1: Edit `config.yaml`**

In `scanner/config.yaml`, under the existing `classification:` block, add the two new lists. Append after the existing keys (`model`, `max_tokens`, `rate_limit_rpm`, `user_context`):

```yaml
  user_aliases:
    - Emile
    - Em
    - Emilio
    - Akgemilio
    - "@AkgEmilio"
    - Akg
  topics_owned:
    - Aave
    - GHO
    - sGHO
    - Logic Protocol
    - USDT0
    - vault
    - Pendle
    - looper
    - treasury
    - Mantle
    - incentives
```

If the existing `classification:` section uses different formatting, match it — only add the two new lists; do not reorder or rewrite existing keys.

- [ ] **Step 10.2: Verify the config loads**

```bash
cd ~/Projects/catchup-dashboard/scanner
python -c "from pathlib import Path; from src.config import ScannerConfig; c = ScannerConfig.from_yaml(Path('config.yaml')); print('aliases:', c.classification.user_aliases); print('topics:', c.classification.topics_owned)"
```

Expected output (env vars must be set):
```
aliases: ['Emile', 'Em', 'Emilio', 'Akgemilio', '@AkgEmilio', 'Akg']
topics: ['Aave', 'GHO', 'sGHO', 'Logic Protocol', 'USDT0', 'vault', 'Pendle', 'looper', 'treasury', 'Mantle', 'incentives']
```

If env vars are not set locally, the loader raises `ValueError: Missing required environment variables: TELEGRAM_API_ID, ...` — that is fine. The VPS has the env set and will load correctly on deploy. Skip this verification step in that case.

- [ ] **Step 10.3: Commit**

```bash
git add scanner/config.yaml
git commit -m "chore(scanner): populate user_aliases and topics_owned in config.yaml"
```

---

## Task 11: Final verification + push

**Files:**
- None (verification only)

- [ ] **Step 11.1: Run the full test suite**

```bash
cd ~/Projects/catchup-dashboard/scanner
pytest -v
```

Expected: all tests green. The new tests added across Tasks 1–9 must all pass. Pre-existing tests must still pass.

- [ ] **Step 11.2: Show all commits on the branch**

```bash
cd ~/Projects/catchup-dashboard
git log --oneline main..HEAD
```

Expected: 11 commits on the branch — 1 spec + 10 feature commits from Tasks 1–10. In reverse chronological order:

```
chore(scanner): populate user_aliases and topics_owned in config.yaml
feat(scanner): enforce P3/MONITORING for unaddressed group chats
feat(scanner): replace SYSTEM_PROMPT with strict-default group rule
feat(scanner): render Telegram reply chains in classifier prompt
feat(scanner): insert YOUR LAST MESSAGE ABOVE anchor in prompt
feat(scanner): inject user_aliases and topics_owned into classifier prompt
feat(scanner): add user_aliases + topics_owned to ClassificationConfig
feat(scanner): capture reply_to_message_id in deep_read
feat(scanner): render reply chains in ChatMessage.format()
feat(scanner): add reply_to_message_id to ChatMessage
docs: design spec for classifier group-chat rework
```

- [ ] **Step 11.3: Push the branch**

```bash
git push -u origin rework/classifier-group-chats
```

- [ ] **Step 11.4: STOP — manual rollout**

Deploy and rollout are user-driven. Do NOT auto-deploy from this plan. Hand back to the user with:

- The branch name (`rework/classifier-group-chats`)
- The expected behavior change: group chats default to P3/MONITORING unless addressed via alias mention, reply-to-user, question-after-anchor, or owned topic
- The verification step on the VPS:
  1. SSH to `vps-7896aeba.vps.ovh.net`
  2. `cd ~/catchup-dashboard && git fetch && git checkout rework/classifier-group-chats`
  3. Trigger a manual scan: send `/scan` to `@akgbaambot` in Telegram
  4. Compare digest output before/after
  5. Observe for 48h and verify escalation reminders drop on group chats
  6. If satisfied, merge to `main` and deploy main on the VPS

---

## Out of scope (do NOT implement in this plan)

- Persisting `addressed_to_user` and `address_reason` to the `triage_items` table
- Dashboard UI changes
- Retroactive reclassification of existing items
- Two-stage classifier (Approach B from brainstorm) — available if Approach A is insufficient
- Rule-based pre-filter (Approach C from brainstorm) — same caveat
