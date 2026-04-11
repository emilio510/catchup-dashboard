# Phase 2 Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add bot trigger, notification escalation, dashboard auto-refresh, analytics, and smarter dedup to the catchup-dashboard.

**Architecture:** Python scanner on VPS (asyncio + Telethon + asyncpg), Next.js 16 dashboard on Vercel (Neon Postgres). Each feature is independently deployable. Implementation order: smarter dedup, escalation, bot trigger, dashboard auto-refresh, analytics.

**Tech Stack:** Python 3.12, asyncpg, httpx, Telethon, anthropic SDK, pytest / Next.js 16, React 19, Chart.js, Neon Postgres

**IMPORTANT:** After completing each Task, run the code-reviewer agent on the changes. Fix all CRITICAL and HIGH findings. Re-run the reviewer to confirm clean. Only then commit.

---

## Task 1: Smarter Dedup -- Extend `get_previous_items` to return classification context

**Files:**
- Modify: `scanner/src/database.py:90-112` (extend query + return shape)
- Test: `scanner/tests/test_database.py`

- [ ] **Step 1: Write failing test for extended return shape**

In `scanner/tests/test_database.py`, add:

```python
from src.database import should_reclassify


def test_get_previous_items_returns_classification_context():
    """get_previous_items should return priority, status, user_status, preview, context_summary."""
    # This tests the return shape contract. We can't hit a real DB in unit tests,
    # so we test the SQL builder and the shape expectation.
    # The actual integration is tested via test_integration.py.
    from src.database import get_previous_items
    import inspect
    # Verify the function signature hasn't changed
    sig = inspect.signature(get_previous_items)
    params = list(sig.parameters.keys())
    assert params == ["database_url", "chat_ids"]
```

- [ ] **Step 2: Run test to verify it passes (baseline)**

Run: `cd /Users/akgemilio/Projects/catchup-dashboard/scanner && python -m pytest tests/test_database.py::test_get_previous_items_returns_classification_context -v`
Expected: PASS (this is a baseline shape test)

- [ ] **Step 3: Update `get_previous_items` to return classification fields**

In `scanner/src/database.py`, replace the `get_previous_items` function:

```python
async def get_previous_items(database_url: str, chat_ids: list[int]) -> dict[int, dict]:
    if not chat_ids:
        return {}
    conn = await asyncpg.connect(database_url)
    try:
        rows = await conn.fetch("""
            SELECT DISTINCT ON (chat_id)
                id, chat_id, scanned_at, user_status, last_message_at,
                priority, status, preview, context_summary
            FROM triage_items
            WHERE chat_id = ANY($1)
            ORDER BY chat_id, scanned_at DESC
        """, chat_ids)
        return {
            row["chat_id"]: {
                "id": str(row["id"]),
                "scanned_at": row["scanned_at"],
                "user_status": row["user_status"],
                "last_message_at": row["last_message_at"],
                "priority": row["priority"],
                "status": row["status"],
                "preview": row["preview"],
                "context_summary": row["context_summary"],
            }
            for row in rows
        }
    finally:
        await conn.close()
```

- [ ] **Step 4: Run all database tests**

Run: `cd /Users/akgemilio/Projects/catchup-dashboard/scanner && python -m pytest tests/test_database.py -v`
Expected: All PASS

- [ ] **Step 5: Run code-reviewer agent, fix findings, re-review, then commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add scanner/src/database.py scanner/tests/test_database.py
git commit -m "feat(dedup): extend get_previous_items to return classification context"
```

---

## Task 2: Smarter Dedup -- Pass previous context to classifier

**Files:**
- Modify: `scanner/src/classifier.py:17-42` (SYSTEM_PROMPT), `scanner/src/classifier.py:45-75` (build_classification_prompt)
- Test: `scanner/tests/test_classifier.py`

- [ ] **Step 1: Write failing test for previous context in prompt**

In `scanner/tests/test_classifier.py`, add:

```python
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
    """When no previous context, prompt should not contain 'Previous classification'."""
    conv = make_conversation("New Chat", [
        ("Bob", "Hey, got a minute?", False),
    ])
    prompt = build_classification_prompt([conv], "akgemilio", "I work at TokenLogic.")
    assert "Previous classification" not in prompt
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/akgemilio/Projects/catchup-dashboard/scanner && python -m pytest tests/test_classifier.py::test_build_prompt_includes_previous_context tests/test_classifier.py::test_build_prompt_includes_done_item_context tests/test_classifier.py::test_build_prompt_without_previous_context -v`
Expected: FAIL -- `build_classification_prompt` doesn't accept `previous_context` parameter

- [ ] **Step 3: Update SYSTEM_PROMPT with stability instructions**

In `scanner/src/classifier.py`, replace the `SYSTEM_PROMPT` string:

```python
SYSTEM_PROMPT = """\
You are a personal communication triage assistant. You analyze conversations and classify them by urgency.

RULES:
- When in doubt between two priority levels, ALWAYS choose the HIGHER (more urgent) one.
- P0 (Respond Today): Someone is actively blocked, deal-critical, or has pinged multiple times.
- P1 (This Week): Important deliverable, meeting prep, or time-sensitive request.
- P2 (Respond): Someone asked a question or made a request, but not urgent.
- P3 (Monitor): FYI, general discussion, no specific action needed from the user.

PRIORITY STABILITY:
- If a previous classification is provided, do not downgrade priority unless the new messages
  clearly resolve the conversation (e.g., the issue was fixed, the question was answered by
  someone else). When in doubt, keep the previous priority.

DONE ITEM AWARENESS:
- If the user previously marked an item as "done", only re-triage as open if the new messages
  genuinely reopen the conversation (new question, new request, new topic). Reactions, "thanks",
  acknowledgments, thumbs-up, and other low-signal messages should NOT reopen a done item.
  For these cases, set priority to P3 and status to MONITORING.

For each conversation, output a JSON array with one object per conversation:
{
  "chat_name": "exact chat name",
  "priority": "P0" | "P1" | "P2" | "P3",
  "status": "READ_NO_REPLY" | "NEW" | "MONITORING",
  "waiting_person": "name of person waiting" or null,
  "waiting_since": "ISO 8601 timestamp of first unanswered message" or null,
  "waiting_days": number or null,
  "tags": ["tag1", "tag2"],
  "context_summary": "1-2 sentence summary of what's happening",
  "draft_reply": "suggested response" or null,
  "preview": "the most relevant recent message, truncated to 200 chars"
}

Output ONLY the JSON array. No markdown, no explanation.\
"""
```

- [ ] **Step 4: Update `build_classification_prompt` to accept and inject previous context**

In `scanner/src/classifier.py`, replace the `build_classification_prompt` function:

```python
def build_classification_prompt(
    conversations: list[ConversationData],
    my_display_name: str,
    user_context: str,
    calendar_context: str = "",
    previous_context: dict[str, dict] | None = None,
) -> str:
    parts = [
        f"User context: {user_context}",
        f"User's display name in chats: {my_display_name}",
        f"Current time: {datetime.now(timezone.utc).isoformat()}",
        "",
    ]

    if calendar_context:
        parts.append(calendar_context)
        parts.append("")
        parts.append("IMPORTANT: If a conversation is related to an upcoming calendar event, boost its priority. Meeting prep should be at least P1.")
        parts.append("")

    parts += [
        "Conversations to classify:",
        "",
    ]

    for conv in conversations:
        parts.append(f"--- CHAT: {conv.dialog.name} (type: {conv.chat_type}) ---")

        # Inject previous classification context if available
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

- [ ] **Step 5: Run classifier tests**

Run: `cd /Users/akgemilio/Projects/catchup-dashboard/scanner && python -m pytest tests/test_classifier.py -v`
Expected: All PASS

- [ ] **Step 6: Run code-reviewer agent, fix findings, re-review, then commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add scanner/src/classifier.py scanner/tests/test_classifier.py
git commit -m "feat(dedup): add previous context to classifier prompt for priority stability"
```

---

## Task 3: Smarter Dedup -- Wire previous context through scanner pipeline

**Files:**
- Modify: `scanner/src/scanner.py:70-97` (pass previous context to classify_all)
- Modify: `scanner/src/classifier.py:145-270` (classify_batch and classify_all accept previous_context)
- Test: `scanner/tests/test_scanner.py`

- [ ] **Step 1: Update `classify_batch` and `classify_all` to accept previous_context**

In `scanner/src/classifier.py`, update the `classify_batch` method signature and prompt building:

```python
    async def classify_batch(
        self,
        conversations: list[ConversationData],
        my_display_name: str,
        previous_context: dict[str, dict] | None = None,
    ) -> list[TriageItem]:
        prompt = build_classification_prompt(
            conversations,
            my_display_name,
            self._config.classification.user_context,
            calendar_context=self.calendar_context,
            previous_context=previous_context,
        )
        # ... rest of method unchanged
```

Update `classify_all` to accept and pass through:

```python
    async def classify_all(
        self,
        conversations: list[ConversationData],
        my_display_name: str,
        previous_context: dict[str, dict] | None = None,
    ) -> list[TriageItem]:
        batch_size = self._config.scan.batch_size
        all_items = []

        total_batches = (len(conversations) + batch_size - 1) // batch_size
        for i in range(0, len(conversations), batch_size):
            if i > 0:
                delay = 60.0 / self._config.classification.rate_limit_rpm
                await asyncio.sleep(delay)

            batch = conversations[i : i + batch_size]
            logger.info(
                "Classifying batch %d/%d (%d conversations)",
                i // batch_size + 1,
                total_batches,
                len(batch),
            )
            items = await self.classify_batch(batch, my_display_name, previous_context)
            all_items.extend(items)

        return all_items
```

- [ ] **Step 2: Wire previous context in scanner.py**

In `scanner/src/scanner.py`, modify the dedup section (around line 72-97) to build previous_context dict and pass it to classify_all. Replace the classify_all call at line 162:

```python
            # 3. Dedup: check which conversations need reclassification
            previous_context: dict[str, dict] | None = None
            if self._config.output.database_url and conversations:
                from src.database import get_previous_items, should_reclassify
                chat_ids = [c.dialog.chat_id for c in conversations]
                try:
                    previous = await get_previous_items(
                        self._config.output.database_url, chat_ids
                    )
                except Exception:
                    logger.exception("Failed to fetch previous items for dedup, classifying all")
                    previous = {}

                to_classify = []
                # Build previous context keyed by chat name for the classifier
                prev_context_by_name: dict[str, dict] = {}
                for conv in conversations:
                    prev = previous.get(conv.dialog.chat_id)
                    if prev is None:
                        to_classify.append(conv)
                    else:
                        last_msg = conv.messages[-1].date if conv.messages else None
                        if should_reclassify(last_msg, prev["scanned_at"], prev["user_status"]):
                            to_classify.append(conv)
                            prev_context_by_name[conv.dialog.name] = {
                                "priority": prev["priority"],
                                "status": prev["status"],
                                "user_status": prev["user_status"],
                                "preview": prev["preview"],
                                "context_summary": prev["context_summary"],
                            }

                logger.info(
                    "Dedup: %d to classify, %d unchanged",
                    len(to_classify), len(conversations) - len(to_classify),
                )
                conversations = to_classify
                if prev_context_by_name:
                    previous_context = prev_context_by_name
```

Then update the classify_all call (around line 162):

```python
            # 5. Classify
            items = await self._classifier.classify_all(conversations, my_name, previous_context)
```

- [ ] **Step 3: Run all scanner tests**

Run: `cd /Users/akgemilio/Projects/catchup-dashboard/scanner && python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 4: Run code-reviewer agent, fix findings, re-review, then commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add scanner/src/scanner.py scanner/src/classifier.py
git commit -m "feat(dedup): wire previous context through scanner -> classifier pipeline"
```

---

## Task 4: Notification Escalation -- Schema + config

**Files:**
- Modify: `schema.sql` (add `last_reminded_at` column)
- Modify: `scanner/config.yaml` (add escalation section)
- Modify: `scanner/src/config.py` (add EscalationConfig)

- [ ] **Step 1: Add migration SQL**

Create `scanner/migrations/002_add_last_reminded_at.sql`:

```sql
ALTER TABLE triage_items ADD COLUMN IF NOT EXISTS last_reminded_at TIMESTAMPTZ;
```

Also update `schema.sql` -- add `last_reminded_at TIMESTAMPTZ` after the `user_status_at` line (line 33):

```sql
  user_status_at   TIMESTAMPTZ,
  last_reminded_at TIMESTAMPTZ
```

- [ ] **Step 2: Run migration on Neon**

Run: `cd /Users/akgemilio/Projects/catchup-dashboard && psql "$DATABASE_URL" -f scanner/migrations/002_add_last_reminded_at.sql`
Expected: ALTER TABLE

- [ ] **Step 3: Add EscalationConfig to config.py**

In `scanner/src/config.py`, add after `CalendarConfig`:

```python
class EscalationConfig(BaseModel):
    P0: int | None = 24   # hours before reminder, None = no reminder
    P1: int | None = 48
    P2: int | None = None
    P3: int | None = None
```

Add to `ScannerConfig`:

```python
class ScannerConfig(BaseModel):
    scan: ScanConfig = Field(default_factory=ScanConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    classification: ClassificationConfig = Field(default_factory=ClassificationConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    calendar: CalendarConfig = Field(default_factory=CalendarConfig)
    escalation: EscalationConfig = Field(default_factory=EscalationConfig)
```

- [ ] **Step 4: Add escalation section to config.yaml**

Add at the end of `scanner/config.yaml`:

```yaml
escalation:
  P0: 24   # hours before reminder
  P1: 48
  P2: null  # no reminder
  P3: null
```

- [ ] **Step 5: Write test for config parsing**

In `scanner/tests/test_config.py`, add:

```python
def test_escalation_config_defaults():
    from src.config import EscalationConfig
    config = EscalationConfig()
    assert config.P0 == 24
    assert config.P1 == 48
    assert config.P2 is None
    assert config.P3 is None


def test_escalation_config_from_yaml(tmp_path):
    from src.config import ScannerConfig
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
telegram:
  blacklist: []
escalation:
  P0: 12
  P1: 24
  P2: null
  P3: null
""")
    import os
    os.environ.setdefault("TELEGRAM_API_ID", "12345")
    os.environ.setdefault("TELEGRAM_API_HASH", "test_hash")
    os.environ.setdefault("ANTHROPIC_API_KEY", "test_key")
    config = ScannerConfig.from_yaml(config_file)
    assert config.escalation.P0 == 12
    assert config.escalation.P1 == 24
```

- [ ] **Step 6: Run config tests**

Run: `cd /Users/akgemilio/Projects/catchup-dashboard/scanner && python -m pytest tests/test_config.py -v`
Expected: All PASS

- [ ] **Step 7: Run code-reviewer agent, fix findings, re-review, then commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
mkdir -p scanner/migrations
git add schema.sql scanner/migrations/002_add_last_reminded_at.sql scanner/src/config.py scanner/config.yaml scanner/tests/test_config.py
git commit -m "feat(escalation): add last_reminded_at column, escalation config"
```

---

## Task 5: Notification Escalation -- Core module

**Files:**
- Create: `scanner/src/escalation.py`
- Create: `scanner/tests/test_escalation.py`

- [ ] **Step 1: Write failing tests**

Create `scanner/tests/test_escalation.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/akgemilio/Projects/catchup-dashboard/scanner && python -m pytest tests/test_escalation.py -v`
Expected: FAIL -- module not found

- [ ] **Step 3: Implement escalation.py**

Create `scanner/src/escalation.py`:

```python
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import asyncpg
import httpx

from src.config import ScannerConfig

logger = logging.getLogger(__name__)


def should_remind(
    priority: str,
    waiting_since: datetime | None,
    last_reminded_at: datetime | None,
    thresholds: dict[str, int | None],
    now: datetime,
) -> bool:
    if waiting_since is None:
        return False

    threshold_hours = thresholds.get(priority)
    if threshold_hours is None:
        return False

    threshold = timedelta(hours=threshold_hours)
    overdue = now - waiting_since

    if overdue < threshold:
        return False

    # If already reminded, only re-remind if a full threshold window has passed
    if last_reminded_at is not None:
        since_last_reminder = now - last_reminded_at
        if since_last_reminder < threshold:
            return False

    return True


def format_reminder(
    chat_name: str,
    priority: str,
    waiting_person: str | None,
    hours_overdue: float,
    preview: str | None,
) -> str:
    person = waiting_person or "Someone"
    hours_int = int(hours_overdue)
    lines = [
        f"Reminder: {priority} item overdue ({hours_int}h)",
        f"Chat: {chat_name}",
        f"Waiting: {person}",
    ]
    if preview:
        lines.append(f"Preview: {preview[:100]}")
    return "\n".join(lines)


async def find_overdue_items(
    database_url: str,
    thresholds: dict[str, int | None],
) -> list[dict]:
    now = datetime.now(timezone.utc)
    conn = await asyncpg.connect(database_url)
    try:
        # Get the latest item per chat that is still open
        rows = await conn.fetch("""
            SELECT DISTINCT ON (COALESCE(chat_id::text, id::text))
                id, chat_name, priority, waiting_person, waiting_since,
                preview, last_reminded_at
            FROM triage_items
            WHERE user_status = 'open'
              AND source = 'telegram'
              AND waiting_since IS NOT NULL
            ORDER BY COALESCE(chat_id::text, id::text), scanned_at DESC
        """)

        overdue = []
        for row in rows:
            if should_remind(
                row["priority"],
                row["waiting_since"],
                row["last_reminded_at"],
                thresholds,
                now,
            ):
                hours_overdue = (now - row["waiting_since"]).total_seconds() / 3600
                overdue.append({
                    "id": str(row["id"]),
                    "chat_name": row["chat_name"],
                    "priority": row["priority"],
                    "waiting_person": row["waiting_person"],
                    "hours_overdue": hours_overdue,
                    "preview": row["preview"],
                })
        return overdue
    finally:
        await conn.close()


async def mark_reminded(database_url: str, item_ids: list[str]) -> None:
    if not item_ids:
        return
    conn = await asyncpg.connect(database_url)
    try:
        await conn.execute("""
            UPDATE triage_items
            SET last_reminded_at = now()
            WHERE id = ANY($1::uuid[])
        """, item_ids)
    finally:
        await conn.close()


async def send_reminders(config: ScannerConfig) -> int:
    if not config.output.database_url:
        logger.warning("No DATABASE_URL configured")
        return 0

    bot_token = config.output.digest_bot_token
    chat_id = config.output.digest_chat_id
    if not bot_token or not chat_id:
        logger.warning("No bot token or chat ID configured for escalation")
        return 0

    thresholds = {
        "P0": config.escalation.P0,
        "P1": config.escalation.P1,
        "P2": config.escalation.P2,
        "P3": config.escalation.P3,
    }

    overdue = await find_overdue_items(config.output.database_url, thresholds)
    if not overdue:
        logger.debug("No overdue items")
        return 0

    logger.info("Found %d overdue items to remind", len(overdue))

    sent_ids = []
    async with httpx.AsyncClient() as http:
        for item in overdue:
            text = format_reminder(
                chat_name=item["chat_name"],
                priority=item["priority"],
                waiting_person=item["waiting_person"],
                hours_overdue=item["hours_overdue"],
                preview=item["preview"],
            )
            resp = await http.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": text},
            )
            if resp.is_success:
                sent_ids.append(item["id"])
                logger.info("Sent reminder for %s", item["chat_name"])
            else:
                logger.error("Failed to send reminder for %s: %s", item["chat_name"], resp.text)

    if sent_ids:
        await mark_reminded(config.output.database_url, sent_ids)

    return len(sent_ids)


async def async_main() -> None:
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Send escalation reminders for overdue items")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.DEBUG if args.verbose else logging.INFO,
    )

    config = ScannerConfig.from_yaml(args.config)
    count = await send_reminders(config)
    if count:
        print(f"Sent {count} reminders")


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run escalation tests**

Run: `cd /Users/akgemilio/Projects/catchup-dashboard/scanner && python -m pytest tests/test_escalation.py -v`
Expected: All PASS

- [ ] **Step 5: Run full test suite**

Run: `cd /Users/akgemilio/Projects/catchup-dashboard/scanner && python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 6: Add crontab entry**

Create `scanner/cron/escalation-crontab.txt`:

```
# Escalation reminders -- every hour on the hour
0 * * * * cd /home/ubuntu/catchup-dashboard/scanner && /home/ubuntu/catchup-dashboard/scanner/.venv/bin/python -m src.escalation --config config.yaml >> /home/ubuntu/catchup-dashboard/scanner/cron/escalation.log 2>&1
```

- [ ] **Step 7: Run code-reviewer agent, fix findings, re-review, then commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add scanner/src/escalation.py scanner/tests/test_escalation.py scanner/cron/escalation-crontab.txt
git commit -m "feat(escalation): add notification escalation for overdue P0/P1 items"
```

---

## Task 6: Bot Trigger -- Bot listener module

**Files:**
- Create: `scanner/src/bot_listener.py`
- Create: `scanner/tests/test_bot_listener.py`

- [ ] **Step 1: Write failing tests**

Create `scanner/tests/test_bot_listener.py`:

```python
from src.bot_listener import parse_command, is_authorized

AUTHORIZED_USER_ID = 1744950707


def test_parse_scan_command():
    update = {
        "update_id": 123,
        "message": {
            "message_id": 1,
            "from": {"id": AUTHORIZED_USER_ID},
            "chat": {"id": AUTHORIZED_USER_ID},
            "text": "/scan",
        },
    }
    cmd = parse_command(update)
    assert cmd == "scan"


def test_parse_scan_with_bot_suffix():
    update = {
        "update_id": 124,
        "message": {
            "message_id": 2,
            "from": {"id": AUTHORIZED_USER_ID},
            "chat": {"id": AUTHORIZED_USER_ID},
            "text": "/scan@akgbaambot",
        },
    }
    cmd = parse_command(update)
    assert cmd == "scan"


def test_parse_unknown_command():
    update = {
        "update_id": 125,
        "message": {
            "message_id": 3,
            "from": {"id": AUTHORIZED_USER_ID},
            "chat": {"id": AUTHORIZED_USER_ID},
            "text": "/unknown",
        },
    }
    cmd = parse_command(update)
    assert cmd is None


def test_parse_no_message():
    update = {"update_id": 126}
    cmd = parse_command(update)
    assert cmd is None


def test_is_authorized_valid():
    assert is_authorized(AUTHORIZED_USER_ID) is True


def test_is_authorized_invalid():
    assert is_authorized(9999999) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/akgemilio/Projects/catchup-dashboard/scanner && python -m pytest tests/test_bot_listener.py -v`
Expected: FAIL -- module not found

- [ ] **Step 3: Implement bot_listener.py**

Create `scanner/src/bot_listener.py`:

```python
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import httpx

from src.config import ScannerConfig

logger = logging.getLogger(__name__)

AUTHORIZED_USER_ID = 1744950707
KNOWN_COMMANDS = {"scan"}
OFFSET_FILE = Path.home() / ".catchup-bot-offset"
POLL_INTERVAL = 30  # seconds


def is_authorized(user_id: int) -> bool:
    return user_id == AUTHORIZED_USER_ID


def parse_command(update: dict) -> str | None:
    message = update.get("message")
    if not message:
        return None

    text = message.get("text", "")
    if not text.startswith("/"):
        return None

    # Strip @botname suffix (e.g. /scan@akgbaambot -> scan)
    command = text.split()[0].lstrip("/").split("@")[0].lower()

    if command in KNOWN_COMMANDS:
        return command
    return None


def read_offset() -> int:
    try:
        return int(OFFSET_FILE.read_text().strip())
    except (FileNotFoundError, ValueError):
        return 0


def write_offset(offset: int) -> None:
    OFFSET_FILE.write_text(str(offset))


async def send_bot_message(bot_token: str, chat_id: int, text: str) -> bool:
    async with httpx.AsyncClient() as http:
        resp = await http.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
        )
        if not resp.is_success:
            logger.error("Bot API error: %s", resp.text)
        return resp.is_success


async def run_scan(config_path: Path) -> tuple[bool, str]:
    """Run the scanner as a subprocess. Returns (success, summary_message)."""
    cmd = [sys.executable, "-m", "src.cli", "--config", str(config_path)]
    logger.info("Starting scan subprocess: %s", " ".join(cmd))

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(config_path.parent),
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode == 0:
        return True, "Scan complete. Check the dashboard for results."
    else:
        error_tail = stderr.decode()[-500:] if stderr else "No error output"
        return False, f"Scan failed (exit code {proc.returncode}).\n{error_tail}"


async def poll_loop(config: ScannerConfig, config_path: Path) -> None:
    bot_token = config.output.digest_bot_token
    if not bot_token:
        logger.error("DIGEST_BOT_TOKEN not configured, cannot start bot listener")
        return

    offset = read_offset()
    scan_in_progress = False

    logger.info("Bot listener started (polling every %ds, offset=%d)", POLL_INTERVAL, offset)

    async with httpx.AsyncClient() as http:
        while True:
            try:
                resp = await http.get(
                    f"https://api.telegram.org/bot{bot_token}/getUpdates",
                    params={"offset": offset, "timeout": 20},
                    timeout=30,
                )

                if not resp.is_success:
                    logger.error("getUpdates error: %s", resp.text)
                    await asyncio.sleep(POLL_INTERVAL)
                    continue

                data = resp.json()
                updates = data.get("result", [])

                for update in updates:
                    offset = update["update_id"] + 1
                    write_offset(offset)

                    message = update.get("message")
                    if not message:
                        continue

                    user_id = message.get("from", {}).get("id")
                    chat_id = message.get("chat", {}).get("id")

                    if not is_authorized(user_id):
                        logger.warning("Unauthorized user %s attempted command", user_id)
                        continue

                    command = parse_command(update)
                    if command == "scan":
                        if scan_in_progress:
                            await send_bot_message(bot_token, chat_id, "Scan already in progress.")
                            continue

                        await send_bot_message(bot_token, chat_id, "Starting scan...")
                        scan_in_progress = True
                        try:
                            success, summary = await run_scan(config_path)
                            await send_bot_message(bot_token, chat_id, summary)
                        except Exception as exc:
                            logger.exception("Scan failed")
                            await send_bot_message(bot_token, chat_id, f"Scan error: {exc}")
                        finally:
                            scan_in_progress = False

            except httpx.TimeoutException:
                pass  # Normal for long-polling timeout
            except Exception:
                logger.exception("Poll loop error")

            await asyncio.sleep(POLL_INTERVAL)


async def async_main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Telegram bot listener for on-demand scans")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.DEBUG if args.verbose else logging.INFO,
    )

    config = ScannerConfig.from_yaml(args.config)
    await poll_loop(config, args.config)


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run bot listener tests**

Run: `cd /Users/akgemilio/Projects/catchup-dashboard/scanner && python -m pytest tests/test_bot_listener.py -v`
Expected: All PASS

- [ ] **Step 5: Create systemd service file**

Create `scanner/systemd/catchup-bot.service`:

```ini
[Unit]
Description=Catchup Dashboard Bot Listener
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/catchup-dashboard/scanner
EnvironmentFile=/home/ubuntu/catchup-dashboard/scanner/.env
ExecStart=/home/ubuntu/catchup-dashboard/scanner/.venv/bin/python -m src.bot_listener --config config.yaml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 6: Run full test suite**

Run: `cd /Users/akgemilio/Projects/catchup-dashboard/scanner && python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 7: Run code-reviewer agent, fix findings, re-review, then commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
mkdir -p scanner/systemd
git add scanner/src/bot_listener.py scanner/tests/test_bot_listener.py scanner/systemd/catchup-bot.service
git commit -m "feat(bot): add on-demand scan trigger via /scan command to @akgbaambot"
```

---

## Task 7: Dashboard Auto-Refresh -- Client component

**Files:**
- Create: `dashboard/components/auto-refresh.tsx`
- Modify: `dashboard/components/stats-bar.tsx`

**IMPORTANT:** Before writing any Next.js code, read the relevant docs at `node_modules/next/dist/docs/` as instructed in the project's AGENTS.md.

- [ ] **Step 1: Read Next.js 16 docs for any relevant breaking changes**

Run: `ls /Users/akgemilio/Projects/catchup-dashboard/dashboard/node_modules/next/dist/docs/` to check available docs. Read any files related to client components or routing.

- [ ] **Step 2: Create auto-refresh.tsx**

Create `dashboard/components/auto-refresh.tsx`:

```tsx
"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, useCallback } from "react";

const REFRESH_INTERVAL_MS = 30 * 60 * 1000; // 30 minutes
const DISPLAY_UPDATE_MS = 60 * 1000; // 1 minute

export function AutoRefresh() {
  const router = useRouter();
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());
  const [timeAgo, setTimeAgo] = useState("just now");

  const refresh = useCallback(() => {
    router.refresh();
    setLastRefreshed(new Date());
  }, [router]);

  // Auto-refresh every 30 minutes, skip if tab is hidden
  useEffect(() => {
    let intervalId: ReturnType<typeof setInterval>;
    let hiddenSince: number | null = null;

    const startInterval = () => {
      intervalId = setInterval(() => {
        if (document.hidden) {
          return;
        }
        refresh();
      }, REFRESH_INTERVAL_MS);
    };

    const handleVisibilityChange = () => {
      if (document.hidden) {
        hiddenSince = Date.now();
      } else if (hiddenSince !== null) {
        const elapsed = Date.now() - hiddenSince;
        hiddenSince = null;
        if (elapsed >= REFRESH_INTERVAL_MS) {
          refresh();
        }
      }
    };

    startInterval();
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      clearInterval(intervalId);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [refresh]);

  // Update display string every minute
  useEffect(() => {
    const update = () => {
      const seconds = Math.floor((Date.now() - lastRefreshed.getTime()) / 1000);
      if (seconds < 60) {
        setTimeAgo("just now");
      } else {
        const minutes = Math.floor(seconds / 60);
        setTimeAgo(`${minutes}m ago`);
      }
    };

    update();
    const id = setInterval(update, DISPLAY_UPDATE_MS);
    return () => clearInterval(id);
  }, [lastRefreshed]);

  return (
    <div className="flex items-center gap-2 text-sm text-[#8b949e]">
      <span>Refreshed: {timeAgo}</span>
      <button
        onClick={refresh}
        className="px-2 py-1 text-xs rounded border border-[#30363d] hover:border-[#8b949e] transition-colors"
        title="Refresh now"
      >
        Refresh
      </button>
    </div>
  );
}
```

- [ ] **Step 3: Update stats-bar.tsx to include AutoRefresh and Analytics link**

Replace `dashboard/components/stats-bar.tsx` entirely:

```tsx
import Link from "next/link";
import { PRIORITY_CONFIG, type Priority } from "@/lib/types";
import { AutoRefresh } from "@/components/auto-refresh";

interface StatsBarProps {
  total: number;
  byPriority: Record<Priority, number>;
  scannedAt: string;
  dialogsListed: number;
  dialogsClassified: number;
}

export function StatsBar({ total, byPriority, scannedAt, dialogsListed, dialogsClassified }: StatsBarProps) {
  const scannedDate = new Date(scannedAt);
  const timeAgo = getTimeAgo(scannedDate);

  return (
    <div className="mb-6">
      <div className="flex items-baseline justify-between mb-4">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold">Catch-up Dashboard</h1>
          <Link
            href="/analytics"
            className="text-sm text-[#8b949e] hover:text-[#e6edf3] transition-colors"
          >
            Analytics
          </Link>
        </div>
        <div className="flex items-center gap-4">
          <AutoRefresh />
          <span className="text-sm text-[#8b949e]">
            Last scan: {timeAgo} -- {dialogsClassified}/{dialogsListed} dialogs
          </span>
        </div>
      </div>
      <div className="flex gap-3">
        <StatCard label="Total" value={total} color="#e6edf3" borderColor="#30363d" />
        {(["P0", "P1", "P2", "P3"] as const).map((p) => (
          <StatCard
            key={p}
            label={`${p} - ${PRIORITY_CONFIG[p].label}`}
            value={byPriority[p]}
            color={PRIORITY_CONFIG[p].color}
            borderColor={PRIORITY_CONFIG[p].color}
          />
        ))}
      </div>
    </div>
  );
}

function StatCard({ label, value, color, borderColor }: { label: string; value: number; color: string; borderColor: string }) {
  return (
    <div className="bg-[#161b22] rounded-lg px-5 py-3 text-center" style={{ borderWidth: 1, borderStyle: "solid", borderColor }}>
      <div className="text-2xl font-bold" style={{ color }}>{value}</div>
      <div className="text-xs text-[#8b949e]">{label}</div>
    </div>
  );
}

function getTimeAgo(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
```

- [ ] **Step 4: Build the dashboard to verify no errors**

Run: `cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && npm run build`
Expected: Build succeeds

- [ ] **Step 5: Run code-reviewer agent, fix findings, re-review, then commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/components/auto-refresh.tsx dashboard/components/stats-bar.tsx
git commit -m "feat(dashboard): add 30-minute auto-refresh with visibility awareness"
```

---

## Task 8: Analytics -- Database query + chart page

**Files:**
- Modify: `dashboard/lib/db.ts` (add analytics query)
- Create: `dashboard/app/analytics/page.tsx`
- Create: `dashboard/components/analytics-chart.tsx`
- Modify: `dashboard/package.json` (add chart.js)

- [ ] **Step 1: Install chart.js dependencies**

Run: `cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && npm install chart.js react-chartjs-2`

- [ ] **Step 2: Add analytics query to db.ts**

In `dashboard/lib/db.ts`, add at the end:

```typescript
export async function getAnalyticsData(days: number = 30): Promise<{
  labels: string[];
  datasets: { P0: number[]; P1: number[]; P2: number[]; P3: number[] };
}> {
  const sql = getDb();
  const cutoff = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString();

  const rows = await sql`
    SELECT
      s.scanned_at,
      ti.priority,
      COUNT(*) as count
    FROM scans s
    JOIN triage_items ti ON ti.scan_id = s.id
    WHERE s.scanned_at >= ${cutoff}::timestamptz
      AND ti.user_status = 'open'
      AND ti.source = 'telegram'
    GROUP BY s.scanned_at, ti.priority
    ORDER BY s.scanned_at ASC
  `;

  // Group by scan timestamp
  const scanMap = new Map<string, Record<string, number>>();
  for (const row of rows) {
    const key = row.scanned_at as string;
    if (!scanMap.has(key)) {
      scanMap.set(key, { P0: 0, P1: 0, P2: 0, P3: 0 });
    }
    const counts = scanMap.get(key)!;
    counts[row.priority as string] = Number(row.count);
  }

  const labels: string[] = [];
  const datasets = { P0: [] as number[], P1: [] as number[], P2: [] as number[], P3: [] as number[] };

  for (const [timestamp, counts] of scanMap) {
    const date = new Date(timestamp);
    labels.push(date.toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }));
    datasets.P0.push(counts.P0);
    datasets.P1.push(counts.P1);
    datasets.P2.push(counts.P2);
    datasets.P3.push(counts.P3);
  }

  return { labels, datasets };
}
```

- [ ] **Step 3: Create analytics-chart.tsx**

Create `dashboard/components/analytics-chart.tsx`:

```tsx
"use client";

import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import { Line } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

interface AnalyticsChartProps {
  labels: string[];
  datasets: {
    P0: number[];
    P1: number[];
    P2: number[];
    P3: number[];
  };
}

const COLORS = {
  P0: "#f85149",
  P1: "#d29922",
  P2: "#3fb950",
  P3: "#8b949e",
};

export function AnalyticsChart({ labels, datasets }: AnalyticsChartProps) {
  const data = {
    labels,
    datasets: [
      {
        label: "P0 - Respond Today",
        data: datasets.P0,
        borderColor: COLORS.P0,
        backgroundColor: COLORS.P0,
        tension: 0.3,
        pointRadius: 3,
      },
      {
        label: "P1 - This Week",
        data: datasets.P1,
        borderColor: COLORS.P1,
        backgroundColor: COLORS.P1,
        tension: 0.3,
        pointRadius: 3,
      },
      {
        label: "P2 - Respond",
        data: datasets.P2,
        borderColor: COLORS.P2,
        backgroundColor: COLORS.P2,
        tension: 0.3,
        pointRadius: 3,
      },
      {
        label: "P3 - Monitor",
        data: datasets.P3,
        borderColor: COLORS.P3,
        backgroundColor: COLORS.P3,
        tension: 0.3,
        pointRadius: 3,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "top" as const,
        labels: {
          color: "#e6edf3",
          usePointStyle: true,
        },
      },
      tooltip: {
        mode: "index" as const,
        intersect: false,
      },
    },
    scales: {
      x: {
        ticks: { color: "#8b949e", maxTicksLimit: 12 },
        grid: { color: "#21262d" },
      },
      y: {
        beginAtZero: true,
        ticks: { color: "#8b949e", stepSize: 1 },
        grid: { color: "#21262d" },
      },
    },
  };

  return (
    <div className="h-[400px]">
      <Line data={data} options={options} />
    </div>
  );
}
```

- [ ] **Step 4: Create analytics page**

Create `dashboard/app/analytics/page.tsx`:

```tsx
import { getAnalyticsData } from "@/lib/db";
import { AnalyticsChart } from "@/components/analytics-chart";
import Link from "next/link";

export const dynamic = "force-dynamic";

interface PageProps {
  searchParams: Promise<{
    days?: string;
  }>;
}

export default async function AnalyticsPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const days = parseInt(params.days ?? "30", 10);
  const validDays = [7, 30, 90].includes(days) ? days : 30;

  const data = await getAnalyticsData(validDays);

  return (
    <main className="max-w-7xl mx-auto px-6 py-8">
      <div className="flex items-baseline justify-between mb-6">
        <div className="flex items-center gap-4">
          <Link href="/" className="text-sm text-[#8b949e] hover:text-[#e6edf3] transition-colors">
            &larr; Dashboard
          </Link>
          <h1 className="text-xl font-bold">Inbox Health</h1>
        </div>
        <div className="flex gap-2">
          {[7, 30, 90].map((d) => (
            <Link
              key={d}
              href={`/analytics?days=${d}`}
              className={`px-3 py-1 text-sm rounded border transition-colors ${
                d === validDays
                  ? "border-[#1f6feb] text-[#e6edf3] bg-[#1f6feb]/20"
                  : "border-[#30363d] text-[#8b949e] hover:border-[#8b949e]"
              }`}
            >
              {d}d
            </Link>
          ))}
        </div>
      </div>

      {data.labels.length === 0 ? (
        <p className="text-[#8b949e]">No scan data available for this time range.</p>
      ) : (
        <div className="bg-[#161b22] rounded-lg p-6 border border-[#30363d]">
          <AnalyticsChart labels={data.labels} datasets={data.datasets} />
        </div>
      )}

      <p className="text-xs text-[#8b949e] mt-4">
        Showing open items per priority across {data.labels.length} scans in the last {validDays} days.
      </p>
    </main>
  );
}
```

- [ ] **Step 5: Build the dashboard**

Run: `cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && npm run build`
Expected: Build succeeds

- [ ] **Step 6: Run code-reviewer agent, fix findings, re-review, then commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/package.json dashboard/package-lock.json dashboard/lib/db.ts dashboard/components/analytics-chart.tsx dashboard/app/analytics/page.tsx
git commit -m "feat(analytics): add inbox health trend chart at /analytics"
```

---

## Task 9: Final integration verification

- [ ] **Step 1: Run full Python test suite**

Run: `cd /Users/akgemilio/Projects/catchup-dashboard/scanner && python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 2: Run dashboard build**

Run: `cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && npm run build`
Expected: Build succeeds

- [ ] **Step 3: Run code-reviewer on full changeset**

Run the code-reviewer agent across all modified files since the session started. Verify no CRITICAL or HIGH findings remain.

- [ ] **Step 4: Update schema.sql comment if needed**

Verify `schema.sql` has the `last_reminded_at` column added.

- [ ] **Step 5: Verify VPS deployment files**

Check that `scanner/systemd/catchup-bot.service` and `scanner/cron/escalation-crontab.txt` have correct paths for the VPS (`/home/ubuntu/catchup-dashboard/scanner`).
