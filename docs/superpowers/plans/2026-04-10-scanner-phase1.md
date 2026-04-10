# Scanner Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python scanner that reads Telegram conversations via Telethon, classifies them by priority using Claude API, and outputs structured JSON results.

**Architecture:** On-demand CLI script. Telethon connects as user account, lists dialogs, filters out irrelevant chats, deep-reads remaining ones, sends batches to Claude for classification, outputs JSON + optional Telegram digest. Reuses session file and .env from the old `telegram-claude-bot` project.

**Tech Stack:** Python 3.12+, Telethon 1.37+, anthropic SDK, PyYAML, asyncpg (for Postgres push later -- not in this phase), pydantic (data models + validation)

**Spec:** `docs/specs/2026-04-10-catchup-dashboard-design.md`

**Old project reference:** `~/Projects/telegram-claude-bot/` -- reuse Telethon patterns, session file, .env credentials. Do NOT copy the architecture (always-on userbot with dot-commands). We're building an on-demand scanner.

---

## File Structure

```
catchup-dashboard/
  scanner/
    src/
      __init__.py
      models.py           # Pydantic data models (TriageItem, ScanResult, etc.)
      config.py            # YAML config loader + env vars
      telegram_reader.py   # Telethon: list dialogs, fast filter, deep read
      classifier.py        # Claude API: batch classification
      digest.py            # Telegram digest sender (to Saved Messages)
      scanner.py           # Main orchestrator: wire everything together
      cli.py               # CLI entry point (argparse)
    tests/
      __init__.py
      test_models.py
      test_config.py
      test_telegram_reader.py
      test_classifier.py
      test_digest.py
      test_scanner.py
    config.yaml            # Scanner configuration (blacklist, scan params)
    requirements.txt
    .env                   # Symlink or copy from old project
    pyproject.toml
```

---

### Task 1: Project Setup + Data Models

**Files:**
- Create: `scanner/pyproject.toml`
- Create: `scanner/requirements.txt`
- Create: `scanner/src/__init__.py`
- Create: `scanner/src/models.py`
- Create: `scanner/tests/__init__.py`
- Create: `scanner/tests/test_models.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "catchup-scanner"
version = "0.1.0"
requires-python = ">=3.12"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

- [ ] **Step 2: Create requirements.txt**

```
telethon==1.37.0
anthropic>=0.42.0
pydantic>=2.0.0
pyyaml>=6.0
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

- [ ] **Step 3: Install dependencies**

Run from `catchup-dashboard/scanner/`:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
Expected: all packages install successfully.

- [ ] **Step 4: Create empty __init__.py files**

Create `scanner/src/__init__.py` and `scanner/tests/__init__.py` as empty files.

- [ ] **Step 5: Write failing tests for data models**

```python
# scanner/tests/test_models.py
from datetime import datetime, timezone
from src.models import TriageItem, ScanResult, ScanStats, PriorityStats


def test_triage_item_creation():
    item = TriageItem(
        source="telegram",
        chat_name="Logic Protocol Core",
        chat_type="group",
        waiting_person="Marc",
        preview="What are the vault yield parameters?",
        context_summary="Marc asking about XUSD vault config for Grab integration",
        draft_reply="Hey Marc, the target APY is 8% with a 3-day lockup...",
        priority="P0",
        status="READ_NO_REPLY",
        tags=["deal blocker", "waiting 3 days"],
        last_message_at=datetime(2026, 4, 7, 14, 0, tzinfo=timezone.utc),
        waiting_since=datetime(2026, 4, 7, 14, 0, tzinfo=timezone.utc),
        waiting_days=3,
        chat_id=-1001234567890,
        message_id=42,
    )
    assert item.source == "telegram"
    assert item.priority == "P0"
    assert item.waiting_days == 3


def test_triage_item_rejects_invalid_priority():
    import pytest
    with pytest.raises(Exception):
        TriageItem(
            source="telegram",
            chat_name="Test",
            chat_type="dm",
            preview="hello",
            priority="P5",
            status="READ_NO_REPLY",
        )


def test_triage_item_rejects_invalid_source():
    import pytest
    with pytest.raises(Exception):
        TriageItem(
            source="whatsapp",
            chat_name="Test",
            chat_type="dm",
            preview="hello",
            priority="P0",
            status="READ_NO_REPLY",
        )


def test_scan_stats():
    stats = ScanStats(
        total=34,
        by_priority=PriorityStats(P0=5, P1=8, P2=12, P3=9),
        by_status={"READ_NO_REPLY": 30, "MONITORING": 4},
    )
    assert stats.total == 34
    assert stats.by_priority.P0 == 5


def test_scan_result():
    result = ScanResult(
        sources=["telegram"],
        dialogs_listed=80,
        dialogs_filtered=35,
        dialogs_classified=35,
        items=[],
        stats=ScanStats(
            total=0,
            by_priority=PriorityStats(P0=0, P1=0, P2=0, P3=0),
            by_status={},
        ),
    )
    assert result.dialogs_listed == 80
    assert len(result.items) == 0


def test_scan_result_to_json():
    result = ScanResult(
        sources=["telegram"],
        dialogs_listed=10,
        dialogs_filtered=5,
        dialogs_classified=5,
        items=[],
        stats=ScanStats(
            total=0,
            by_priority=PriorityStats(P0=0, P1=0, P2=0, P3=0),
            by_status={},
        ),
    )
    json_str = result.model_dump_json()
    assert '"dialogs_listed": 10' in json_str or '"dialogs_listed":10' in json_str
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `cd scanner && python -m pytest tests/test_models.py -v`
Expected: FAIL -- `ModuleNotFoundError: No module named 'src.models'`

- [ ] **Step 7: Implement data models**

```python
# scanner/src/models.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


Source = Literal["telegram", "notion", "github", "calendar"]
Priority = Literal["P0", "P1", "P2", "P3"]
Status = Literal["NEW", "READ_NO_REPLY", "REPLIED", "MONITORING"]
ChatType = Literal["dm", "group"]
UserStatus = Literal["open", "done", "snoozed"]


class TriageItem(BaseModel):
    source: Source
    chat_name: str
    chat_type: ChatType
    waiting_person: str | None = None
    preview: str
    context_summary: str | None = None
    draft_reply: str | None = None
    priority: Priority
    status: Status = "READ_NO_REPLY"
    tags: list[str] = Field(default_factory=list)
    last_message_at: datetime | None = None
    waiting_since: datetime | None = None
    waiting_days: int | None = None
    chat_id: int | None = None
    message_id: int | None = None


class PriorityStats(BaseModel):
    P0: int = 0
    P1: int = 0
    P2: int = 0
    P3: int = 0


class ScanStats(BaseModel):
    total: int
    by_priority: PriorityStats
    by_status: dict[str, int] = Field(default_factory=dict)


class ScanResult(BaseModel):
    scanned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sources: list[str]
    dialogs_listed: int
    dialogs_filtered: int
    dialogs_classified: int
    items: list[TriageItem]
    stats: ScanStats
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `cd scanner && python -m pytest tests/test_models.py -v`
Expected: all 6 tests PASS

- [ ] **Step 9: Commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add scanner/pyproject.toml scanner/requirements.txt scanner/src/ scanner/tests/
git commit -m "feat: project setup and pydantic data models"
```

---

### Task 2: Config Loader

**Files:**
- Create: `scanner/config.yaml`
- Create: `scanner/src/config.py`
- Create: `scanner/tests/test_config.py`

- [ ] **Step 1: Create config.yaml**

```yaml
# config.yaml
scan:
  window_days: 7
  messages_per_chat: 20
  batch_size: 5

telegram:
  session_name: akgemilio
  blacklist:
    - "Monitoring Alerts"
    - "DeFi News Channel"
  bot_whitelist: []

classification:
  model: claude-sonnet-4-20250514
  max_tokens: 4096
  rate_limit_rpm: 30
  user_context: |
    I work at TokenLogic (Aave treasury/service provider).
    Building Logic Protocol (cross-chain yield product).
    Key collaborators: StraitsX, Mantle, Aave governance participants.
    I manage incentive programs, vault development, and governance proposals.

output:
  telegram_digest: true
  json_file: scan_results.json
```

- [ ] **Step 2: Write failing tests for config**

```python
# scanner/tests/test_config.py
import os
import tempfile
from pathlib import Path
from src.config import ScannerConfig


def test_load_config_from_yaml():
    yaml_content = """
scan:
  window_days: 7
  messages_per_chat: 20
  batch_size: 5
telegram:
  session_name: testuser
  blacklist:
    - "Spam Group"
  bot_whitelist: []
classification:
  model: claude-sonnet-4-20250514
  max_tokens: 4096
  rate_limit_rpm: 30
  user_context: "Test context"
output:
  telegram_digest: false
  json_file: output.json
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()
        config = ScannerConfig.from_yaml(Path(f.name))

    os.unlink(f.name)

    assert config.scan.window_days == 7
    assert config.scan.batch_size == 5
    assert config.telegram.session_name == "testuser"
    assert "Spam Group" in config.telegram.blacklist
    assert config.classification.model == "claude-sonnet-4-20250514"
    assert config.output.telegram_digest is False


def test_config_loads_env_vars(monkeypatch):
    monkeypatch.setenv("TELEGRAM_API_ID", "12345")
    monkeypatch.setenv("TELEGRAM_API_HASH", "abc123")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")

    yaml_content = """
scan:
  window_days: 3
  messages_per_chat: 10
  batch_size: 3
telegram:
  session_name: test
  blacklist: []
  bot_whitelist: []
classification:
  model: claude-sonnet-4-20250514
  max_tokens: 2048
  rate_limit_rpm: 10
  user_context: "test"
output:
  telegram_digest: false
  json_file: test.json
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()
        config = ScannerConfig.from_yaml(Path(f.name))

    os.unlink(f.name)

    assert config.telegram.api_id == 12345
    assert config.telegram.api_hash == "abc123"
    assert config.classification.api_key == "sk-test"


def test_blacklist_case_insensitive():
    yaml_content = """
scan:
  window_days: 7
  messages_per_chat: 20
  batch_size: 5
telegram:
  session_name: test
  blacklist:
    - "Monitoring Alerts"
  bot_whitelist: []
classification:
  model: claude-sonnet-4-20250514
  max_tokens: 4096
  rate_limit_rpm: 30
  user_context: "test"
output:
  telegram_digest: false
  json_file: test.json
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()
        config = ScannerConfig.from_yaml(Path(f.name))

    os.unlink(f.name)

    assert config.is_blacklisted("monitoring alerts")
    assert config.is_blacklisted("MONITORING ALERTS")
    assert config.is_blacklisted("Monitoring Alerts")
    assert not config.is_blacklisted("Real Group")
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd scanner && python -m pytest tests/test_config.py -v`
Expected: FAIL -- `ModuleNotFoundError: No module named 'src.config'`

- [ ] **Step 4: Implement config loader**

```python
# scanner/src/config.py
from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv()


class ScanConfig(BaseModel):
    window_days: int = 7
    messages_per_chat: int = 20
    batch_size: int = 5


class TelegramConfig(BaseModel):
    session_name: str = "akgemilio"
    blacklist: list[str] = Field(default_factory=list)
    bot_whitelist: list[str] = Field(default_factory=list)
    api_id: int = 0
    api_hash: str = ""


class ClassificationConfig(BaseModel):
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    rate_limit_rpm: int = 30
    user_context: str = ""
    api_key: str = ""


class OutputConfig(BaseModel):
    telegram_digest: bool = True
    json_file: str = "scan_results.json"


class ScannerConfig(BaseModel):
    scan: ScanConfig = Field(default_factory=ScanConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    classification: ClassificationConfig = Field(default_factory=ClassificationConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)

    @classmethod
    def from_yaml(cls, path: Path) -> ScannerConfig:
        with open(path) as f:
            data = yaml.safe_load(f) or {}

        config = cls(**data)

        # Overlay env vars (secrets never go in YAML)
        config.telegram.api_id = int(os.environ.get("TELEGRAM_API_ID", "0"))
        config.telegram.api_hash = os.environ.get("TELEGRAM_API_HASH", "")
        config.classification.api_key = os.environ.get("ANTHROPIC_API_KEY", "")

        return config

    def is_blacklisted(self, chat_name: str) -> bool:
        lower_name = chat_name.lower()
        return any(b.lower() == lower_name for b in self.telegram.blacklist)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd scanner && python -m pytest tests/test_config.py -v`
Expected: all 3 tests PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add scanner/config.yaml scanner/src/config.py scanner/tests/test_config.py
git commit -m "feat: YAML config loader with env var overlay"
```

---

### Task 3: Telegram Reader (List + Filter + Deep Read)

**Files:**
- Create: `scanner/src/telegram_reader.py`
- Create: `scanner/tests/test_telegram_reader.py`

This is the core Telethon integration. Tests use mocks since we can't hit Telegram in CI.

- [ ] **Step 1: Write failing tests for telegram reader**

```python
# scanner/tests/test_telegram_reader.py
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from src.telegram_reader import (
    TelegramReader,
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


def test_should_not_filter_outside_window():
    config = make_config()
    old_date = datetime.now(timezone.utc) - timedelta(days=10)
    dialog = DialogInfo(
        chat_id=6, name="Old Chat", is_channel=False, is_bot=False,
        last_message_sender_is_me=False, last_message_date=old_date,
    )
    # Outside 7-day window, should be filtered
    assert should_filter_dialog(dialog, config) is True


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd scanner && python -m pytest tests/test_telegram_reader.py -v`
Expected: FAIL -- `ModuleNotFoundError`

- [ ] **Step 3: Implement telegram reader**

```python
# scanner/src/telegram_reader.py
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from telethon import TelegramClient
from telethon.tl.types import User, Chat, Channel

from src.config import ScannerConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DialogInfo:
    chat_id: int
    name: str
    is_channel: bool
    is_bot: bool
    last_message_sender_is_me: bool
    last_message_date: datetime | None


@dataclass(frozen=True)
class ChatMessage:
    sender_name: str
    sender_id: int
    text: str
    date: datetime
    message_id: int
    is_me: bool

    def format(self) -> str:
        tag = " (me)" if self.is_me else ""
        ts = self.date.strftime("%Y-%m-%d %H:%M")
        return f"[{ts}] {self.sender_name}{tag}: {self.text}"


@dataclass(frozen=True)
class ConversationData:
    dialog: DialogInfo
    messages: list[ChatMessage]
    chat_type: str  # "dm" or "group"


def should_filter_dialog(dialog: DialogInfo, config: ScannerConfig) -> bool:
    if config.is_blacklisted(dialog.name):
        return True
    if dialog.is_channel:
        return True
    if dialog.is_bot and dialog.name not in config.telegram.bot_whitelist:
        return True
    if dialog.last_message_sender_is_me:
        return True
    if dialog.last_message_date is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=config.scan.window_days)
        if dialog.last_message_date < cutoff:
            return True
    return False


class TelegramReader:
    def __init__(self, config: ScannerConfig) -> None:
        self._config = config
        self._client: TelegramClient | None = None
        self._me_id: int | None = None

    async def connect(self) -> None:
        self._client = TelegramClient(
            self._config.telegram.session_name,
            self._config.telegram.api_id,
            self._config.telegram.api_hash,
        )
        await self._client.start()
        me = await self._client.get_me()
        self._me_id = me.id
        logger.info("Connected as %s (ID: %s)", me.first_name, me.id)

    async def disconnect(self) -> None:
        if self._client:
            await self._client.disconnect()

    async def list_dialogs(self) -> list[DialogInfo]:
        assert self._client is not None
        dialogs = []
        async for d in self._client.iter_dialogs():
            entity = d.entity
            is_channel = isinstance(entity, Channel) and entity.broadcast
            is_bot = isinstance(entity, User) and bool(entity.bot)

            last_msg = d.message
            last_sender_is_me = (
                last_msg is not None and last_msg.sender_id == self._me_id
            )
            last_date = last_msg.date if last_msg else None

            dialogs.append(
                DialogInfo(
                    chat_id=d.id,
                    name=d.name or str(d.id),
                    is_channel=is_channel,
                    is_bot=is_bot,
                    last_message_sender_is_me=last_sender_is_me,
                    last_message_date=last_date,
                )
            )
        return dialogs

    async def filter_dialogs(
        self, dialogs: list[DialogInfo]
    ) -> tuple[list[DialogInfo], int]:
        kept = [d for d in dialogs if not should_filter_dialog(d, self._config)]
        filtered_count = len(dialogs) - len(kept)
        logger.info(
            "Filtered %d/%d dialogs (kept %d)",
            filtered_count, len(dialogs), len(kept),
        )
        return kept, filtered_count

    async def deep_read(self, dialog: DialogInfo) -> ConversationData:
        assert self._client is not None
        cutoff = datetime.now(timezone.utc) - timedelta(
            days=self._config.scan.window_days
        )
        messages: list[ChatMessage] = []

        async for msg in self._client.iter_messages(
            dialog.chat_id,
            limit=self._config.scan.messages_per_chat,
            offset_date=cutoff,
            reverse=True,
        ):
            if not msg.text:
                continue
            sender_name = "unknown"
            sender_id = msg.sender_id or 0
            if msg.sender:
                if isinstance(msg.sender, User):
                    parts = [msg.sender.first_name or "", msg.sender.last_name or ""]
                    sender_name = " ".join(p for p in parts if p) or str(sender_id)
                elif isinstance(msg.sender, (Chat, Channel)):
                    sender_name = msg.sender.title or str(sender_id)

            messages.append(
                ChatMessage(
                    sender_name=sender_name,
                    sender_id=sender_id,
                    text=msg.text,
                    date=msg.date,
                    message_id=msg.id,
                    is_me=sender_id == self._me_id,
                )
            )

        entity = await self._client.get_entity(dialog.chat_id)
        chat_type = "dm" if isinstance(entity, User) else "group"

        return ConversationData(
            dialog=dialog, messages=messages, chat_type=chat_type
        )

    async def read_all(self) -> tuple[list[ConversationData], int, int]:
        all_dialogs = await self.list_dialogs()
        kept, filtered_count = await self.filter_dialogs(all_dialogs)

        conversations = []
        for dialog in kept:
            try:
                conv = await self.deep_read(dialog)
                if conv.messages:
                    conversations.append(conv)
            except Exception:
                logger.exception("Failed to read dialog: %s", dialog.name)

        return conversations, len(all_dialogs), filtered_count
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd scanner && python -m pytest tests/test_telegram_reader.py -v`
Expected: all 7 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add scanner/src/telegram_reader.py scanner/tests/test_telegram_reader.py
git commit -m "feat: telegram reader with dialog listing, filtering, and deep read"
```

---

### Task 4: AI Classifier

**Files:**
- Create: `scanner/src/classifier.py`
- Create: `scanner/tests/test_classifier.py`

- [ ] **Step 1: Write failing tests for classifier**

```python
# scanner/tests/test_classifier.py
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from src.classifier import Classifier, build_classification_prompt, parse_classification_response
from src.telegram_reader import DialogInfo, ChatMessage, ConversationData
from src.config import ScannerConfig, ClassificationConfig


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd scanner && python -m pytest tests/test_classifier.py -v`
Expected: FAIL -- `ModuleNotFoundError`

- [ ] **Step 3: Implement classifier**

```python
# scanner/src/classifier.py
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import anthropic

from src.config import ScannerConfig
from src.models import TriageItem
from src.telegram_reader import ConversationData

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a personal communication triage assistant. You analyze conversations and classify them by urgency.

RULES:
- When in doubt between two priority levels, ALWAYS choose the HIGHER (more urgent) one.
- P0 (Respond Today): Someone is actively blocked, deal-critical, or has pinged multiple times.
- P1 (This Week): Important deliverable, meeting prep, or time-sensitive request.
- P2 (Respond): Someone asked a question or made a request, but not urgent.
- P3 (Monitor): FYI, general discussion, no specific action needed from the user.

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


def build_classification_prompt(
    conversations: list[ConversationData],
    my_display_name: str,
    user_context: str,
) -> str:
    parts = [
        f"User context: {user_context}",
        f"User's display name in chats: {my_display_name}",
        f"Current time: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Conversations to classify:",
        "",
    ]

    for conv in conversations:
        parts.append(f"--- CHAT: {conv.dialog.name} (type: {conv.chat_type}) ---")
        for msg in conv.messages:
            parts.append(msg.format())
        parts.append("")

    return "\n".join(parts)


def parse_classification_response(
    response_text: str,
    source: str,
    chat_type: str,
    chat_id: int,
    last_message_id: int,
) -> list[TriageItem]:
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        logger.error("Failed to parse classifier response as JSON")
        return []

    if not isinstance(data, list):
        data = [data]

    items = []
    for entry in data:
        try:
            waiting_since = None
            if entry.get("waiting_since"):
                try:
                    waiting_since = datetime.fromisoformat(
                        entry["waiting_since"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            item = TriageItem(
                source=source,
                chat_name=entry.get("chat_name", "Unknown"),
                chat_type=chat_type,
                waiting_person=entry.get("waiting_person"),
                preview=entry.get("preview", ""),
                context_summary=entry.get("context_summary"),
                draft_reply=entry.get("draft_reply"),
                priority=entry.get("priority", "P2"),
                status=entry.get("status", "READ_NO_REPLY"),
                tags=entry.get("tags", []),
                last_message_at=datetime.now(timezone.utc),
                waiting_since=waiting_since,
                waiting_days=entry.get("waiting_days"),
                chat_id=chat_id,
                message_id=last_message_id,
            )
            items.append(item)
        except Exception:
            logger.exception("Failed to parse classification entry: %s", entry)

    return items


class Classifier:
    def __init__(self, config: ScannerConfig) -> None:
        self._config = config
        self._client = anthropic.AsyncAnthropic(api_key=config.classification.api_key)

    async def classify_batch(
        self, conversations: list[ConversationData], my_display_name: str
    ) -> list[TriageItem]:
        prompt = build_classification_prompt(
            conversations,
            my_display_name,
            self._config.classification.user_context,
        )

        response = await self._client.messages.create(
            model=self._config.classification.model,
            max_tokens=self._config.classification.max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = response.content[0].text
        all_items = []

        for conv in conversations:
            last_msg_id = conv.messages[-1].message_id if conv.messages else 0
            items = parse_classification_response(
                response_text,
                source="telegram",
                chat_type=conv.chat_type,
                chat_id=conv.dialog.chat_id,
                last_message_id=last_msg_id,
            )
            all_items.extend(items)

        return all_items

    async def classify_all(
        self,
        conversations: list[ConversationData],
        my_display_name: str,
    ) -> list[TriageItem]:
        batch_size = self._config.scan.batch_size
        all_items = []

        for i in range(0, len(conversations), batch_size):
            batch = conversations[i : i + batch_size]
            logger.info(
                "Classifying batch %d/%d (%d conversations)",
                i // batch_size + 1,
                (len(conversations) + batch_size - 1) // batch_size,
                len(batch),
            )
            items = await self.classify_batch(batch, my_display_name)
            all_items.extend(items)

        return all_items
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd scanner && python -m pytest tests/test_classifier.py -v`
Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add scanner/src/classifier.py scanner/tests/test_classifier.py
git commit -m "feat: AI classifier with batch processing and JSON parsing"
```

---

### Task 5: Telegram Digest Sender

**Files:**
- Create: `scanner/src/digest.py`
- Create: `scanner/tests/test_digest.py`

- [ ] **Step 1: Write failing tests for digest**

```python
# scanner/tests/test_digest.py
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
    assert "P0 (2 items)" in digest
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
    # Should show first 5 and indicate more
    assert "more" in digest.lower() or "+" in digest
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd scanner && python -m pytest tests/test_digest.py -v`
Expected: FAIL

- [ ] **Step 3: Implement digest**

```python
# scanner/src/digest.py
from __future__ import annotations

import logging
from datetime import datetime, timezone

from telethon import TelegramClient

from src.models import ScanResult, TriageItem

logger = logging.getLogger(__name__)

MAX_ITEMS_PER_SECTION = 5


def _format_item(item: TriageItem) -> str:
    person = item.waiting_person or "Someone"
    wait = f" ({item.waiting_days}d)" if item.waiting_days else ""
    preview = item.preview[:80] if item.preview else ""
    return f"  - {item.chat_name}: {person}{wait} -- {preview}"


def format_digest(result: ScanResult, dashboard_url: str | None = None) -> str:
    now = datetime.now(timezone.utc)
    header = f"Catch-up Dashboard -- {now.strftime('%b %d, %H:%M UTC')}"

    if not result.items:
        return f"{header}\n\nNo items requiring attention. All clear."

    sections = []
    priority_labels = {
        "P0": "Respond Today",
        "P1": "This Week",
        "P2": "Respond",
        "P3": "Monitor",
    }

    for priority in ["P0", "P1", "P2", "P3"]:
        items = [i for i in result.items if i.priority == priority]
        if not items:
            continue

        count = len(items)
        label = priority_labels[priority]
        section_lines = [f"{priority} -- {label} ({count} items):"]

        shown = items[:MAX_ITEMS_PER_SECTION]
        for item in shown:
            section_lines.append(_format_item(item))

        remaining = count - len(shown)
        if remaining > 0:
            section_lines.append(f"  + {remaining} more")

        sections.append("\n".join(section_lines))

    body = "\n\n".join(sections)
    footer = f"{result.stats.total} total items"
    if dashboard_url:
        footer += f" | Dashboard: {dashboard_url}"

    return f"{header}\n\n{body}\n\n{footer}"


async def send_digest(
    client: TelegramClient, result: ScanResult, dashboard_url: str | None = None
) -> None:
    text = format_digest(result, dashboard_url)
    await client.send_message("me", text)
    logger.info("Digest sent to Saved Messages")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd scanner && python -m pytest tests/test_digest.py -v`
Expected: all 3 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add scanner/src/digest.py scanner/tests/test_digest.py
git commit -m "feat: telegram digest formatter and sender"
```

---

### Task 6: Main Scanner Orchestrator

**Files:**
- Create: `scanner/src/scanner.py`
- Create: `scanner/tests/test_scanner.py`

- [ ] **Step 1: Write failing test for scanner orchestrator**

```python
# scanner/tests/test_scanner.py
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from src.scanner import Scanner
from src.config import ScannerConfig, ScanConfig, TelegramConfig, ClassificationConfig, OutputConfig
from src.models import TriageItem, ScanResult, ScanStats, PriorityStats
from src.telegram_reader import DialogInfo, ChatMessage, ConversationData


def make_test_config() -> ScannerConfig:
    return ScannerConfig(
        scan=ScanConfig(window_days=7, messages_per_chat=20, batch_size=5),
        telegram=TelegramConfig(
            session_name="test", blacklist=[], bot_whitelist=[],
            api_id=12345, api_hash="hash",
        ),
        classification=ClassificationConfig(
            model="claude-sonnet-4-20250514", max_tokens=4096,
            rate_limit_rpm=30, user_context="test", api_key="sk-test",
        ),
        output=OutputConfig(telegram_digest=False, json_file="test_output.json"),
    )


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scanner && python -m pytest tests/test_scanner.py -v`
Expected: FAIL

- [ ] **Step 3: Implement scanner orchestrator**

```python
# scanner/src/scanner.py
from __future__ import annotations

import json
import logging
from pathlib import Path

from src.classifier import Classifier
from src.config import ScannerConfig
from src.digest import send_digest
from src.models import PriorityStats, ScanResult, ScanStats, TriageItem
from src.telegram_reader import TelegramReader

logger = logging.getLogger(__name__)


class Scanner:
    def __init__(self, config: ScannerConfig) -> None:
        self._config = config
        self._reader = TelegramReader(config)
        self._classifier = Classifier(config)

    @staticmethod
    def _compute_stats(items: list[TriageItem]) -> ScanStats:
        by_priority = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
        by_status: dict[str, int] = {}

        for item in items:
            by_priority[item.priority] = by_priority.get(item.priority, 0) + 1
            by_status[item.status] = by_status.get(item.status, 0) + 1

        return ScanStats(
            total=len(items),
            by_priority=PriorityStats(**by_priority),
            by_status=by_status,
        )

    async def run(self) -> ScanResult:
        logger.info("Starting scan...")

        # 1. Connect to Telegram
        await self._reader.connect()

        try:
            # 2. Read and filter dialogs
            conversations, total_dialogs, filtered_count = (
                await self._reader.read_all()
            )
            logger.info(
                "Read %d conversations (from %d dialogs, %d filtered)",
                len(conversations), total_dialogs, filtered_count,
            )

            if not conversations:
                logger.info("No conversations to classify")
                stats = ScanStats(
                    total=0,
                    by_priority=PriorityStats(),
                    by_status={},
                )
                return ScanResult(
                    sources=["telegram"],
                    dialogs_listed=total_dialogs,
                    dialogs_filtered=len(conversations),
                    dialogs_classified=0,
                    items=[],
                    stats=stats,
                )

            # 3. Get display name for classification
            me = await self._reader._client.get_me()
            my_name = me.first_name or "Me"

            # 4. Classify
            items = await self._classifier.classify_all(conversations, my_name)
            logger.info("Classified %d items", len(items))

            # 5. Sort by priority
            priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
            items.sort(key=lambda i: priority_order.get(i.priority, 99))

            # 6. Build result
            stats = self._compute_stats(items)
            result = ScanResult(
                sources=["telegram"],
                dialogs_listed=total_dialogs,
                dialogs_filtered=len(conversations),
                dialogs_classified=len(conversations),
                items=items,
                stats=stats,
            )

            # 7. Output JSON
            output_path = Path(self._config.output.json_file)
            output_path.write_text(result.model_dump_json(indent=2))
            logger.info("Results written to %s", output_path)

            # 8. Send Telegram digest
            if self._config.output.telegram_digest:
                await send_digest(self._reader._client, result)

            return result

        finally:
            await self._reader.disconnect()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd scanner && python -m pytest tests/test_scanner.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add scanner/src/scanner.py scanner/tests/test_scanner.py
git commit -m "feat: scanner orchestrator wiring reader, classifier, and digest"
```

---

### Task 7: CLI Entry Point

**Files:**
- Create: `scanner/src/cli.py`
- Create: `scanner/.env` (symlink from old project)

- [ ] **Step 1: Create CLI entry point**

```python
# scanner/src/cli.py
from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from src.config import ScannerConfig
from src.scanner import Scanner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Catch-up Dashboard Scanner -- scan Telegram for unanswered messages"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.yaml"),
        help="Path to config.yaml (default: config.yaml)",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=None,
        help="Override scan window in days (default: from config)",
    )
    parser.add_argument(
        "--no-digest",
        action="store_true",
        help="Skip sending Telegram digest",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Override output JSON path",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.DEBUG if args.verbose else logging.INFO,
    )

    config = ScannerConfig.from_yaml(args.config)

    # Apply CLI overrides
    if args.window_days is not None:
        config.scan.window_days = args.window_days
    if args.no_digest:
        config.output.telegram_digest = False
    if args.output is not None:
        config.output.json_file = str(args.output)

    scanner = Scanner(config)
    result = await scanner.run()

    print(f"\nScan complete: {result.stats.total} items found")
    print(f"  P0: {result.stats.by_priority.P0}")
    print(f"  P1: {result.stats.by_priority.P1}")
    print(f"  P2: {result.stats.by_priority.P2}")
    print(f"  P3: {result.stats.by_priority.P3}")
    print(f"\nResults saved to: {config.output.json_file}")


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Symlink .env from old project**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/scanner
ln -s /Users/akgemilio/Projects/telegram-claude-bot/.env .env
```

Verify: `cat .env` should show TELEGRAM_API_ID, TELEGRAM_API_HASH, ANTHROPIC_API_KEY.

- [ ] **Step 3: Copy session file from old project**

```bash
cp /Users/akgemilio/Projects/telegram-claude-bot/akgemilio.session \
   /Users/akgemilio/Projects/catchup-dashboard/scanner/akgemilio.session
```

Note: session file is in .gitignore, will not be committed.

- [ ] **Step 4: Smoke test -- run the scanner dry**

Run from `scanner/`:
```bash
source .venv/bin/activate
python -m src.cli --config config.yaml --no-digest -v
```

Expected: connects to Telegram, lists dialogs, filters, classifies, outputs JSON. First run may prompt for phone number if session expired.

- [ ] **Step 5: Verify output JSON**

```bash
cat scan_results.json | python -m json.tool | head -50
```

Expected: valid JSON with `scanned_at`, `sources`, `items` array, `stats` object.

- [ ] **Step 6: Run full test suite**

```bash
cd scanner && python -m pytest tests/ -v --tb=short
```

Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add scanner/src/cli.py
git commit -m "feat: CLI entry point with arg overrides and smoke test"
```

---

### Task 8: End-to-End Integration Test

**Files:**
- Create: `scanner/tests/test_integration.py`

This task verifies the full pipeline works with mocked Telegram and Claude API.

- [ ] **Step 1: Write integration test**

```python
# scanner/tests/test_integration.py
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from src.scanner import Scanner
from src.config import ScannerConfig, ScanConfig, TelegramConfig, ClassificationConfig, OutputConfig


MOCK_CLAUDE_RESPONSE = json.dumps([
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
    },
    {
        "chat_name": "Mantle Incentives",
        "priority": "P2",
        "status": "READ_NO_REPLY",
        "waiting_person": "Alice",
        "waiting_since": "2026-04-09T10:00:00Z",
        "waiting_days": 1,
        "tags": ["question"],
        "context_summary": "Alice asking about ROI targets",
        "draft_reply": "Hi Alice, the ROI target is...",
        "preview": "What are the ROI targets for this week?",
    },
])


def make_test_config(tmp_path: Path) -> ScannerConfig:
    return ScannerConfig(
        scan=ScanConfig(window_days=7, messages_per_chat=20, batch_size=5),
        telegram=TelegramConfig(
            session_name="test", blacklist=["Spam"], bot_whitelist=[],
            api_id=12345, api_hash="hash",
        ),
        classification=ClassificationConfig(
            model="claude-sonnet-4-20250514", max_tokens=4096,
            rate_limit_rpm=30, user_context="I work at TokenLogic.", api_key="sk-test",
        ),
        output=OutputConfig(
            telegram_digest=False,
            json_file=str(tmp_path / "output.json"),
        ),
    )


@patch("src.scanner.send_digest")
@patch("src.classifier.anthropic.AsyncAnthropic")
@patch("src.telegram_reader.TelegramClient")
async def test_full_pipeline(mock_client_cls, mock_anthropic_cls, mock_send_digest, tmp_path):
    # Mock Telegram client
    mock_client = AsyncMock()
    mock_client_cls.return_value = mock_client

    mock_me = MagicMock()
    mock_me.id = 100
    mock_me.first_name = "Emilio"
    mock_client.get_me.return_value = mock_me
    mock_client.start = AsyncMock()
    mock_client.disconnect = AsyncMock()

    # Mock dialogs
    mock_msg_other = MagicMock()
    mock_msg_other.sender_id = 200
    mock_msg_other.date = datetime(2026, 4, 9, 14, 0, tzinfo=timezone.utc)
    mock_msg_other.text = "What about the vault params?"
    mock_msg_other.id = 42
    mock_msg_other.sender = MagicMock()
    mock_msg_other.sender.first_name = "Marc"
    mock_msg_other.sender.last_name = None
    mock_msg_other.sender.bot = False

    mock_dialog = MagicMock()
    mock_dialog.id = -100123
    mock_dialog.name = "Logic Protocol Core"
    mock_dialog.message = mock_msg_other

    mock_entity_group = MagicMock(spec=[])  # not User, not Channel
    mock_dialog.entity = mock_entity_group

    async def fake_iter_dialogs():
        yield mock_dialog

    mock_client.iter_dialogs = fake_iter_dialogs

    async def fake_iter_messages(*args, **kwargs):
        yield mock_msg_other

    mock_client.iter_messages = fake_iter_messages
    mock_client.get_entity = AsyncMock(return_value=mock_entity_group)

    # Mock Claude API
    mock_anthropic = AsyncMock()
    mock_anthropic_cls.return_value = mock_anthropic
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=MOCK_CLAUDE_RESPONSE)]
    mock_anthropic.messages.create = AsyncMock(return_value=mock_response)

    # Run scanner
    config = make_test_config(tmp_path)
    scanner = Scanner(config)
    result = await scanner.run()

    # Verify
    assert result.stats.total >= 1
    assert result.dialogs_listed == 1
    assert len(result.items) >= 1

    # Verify JSON output
    output_path = Path(config.output.json_file)
    assert output_path.exists()
    output_data = json.loads(output_path.read_text())
    assert "items" in output_data
    assert "stats" in output_data
```

- [ ] **Step 2: Run integration test**

Run: `cd scanner && python -m pytest tests/test_integration.py -v`
Expected: PASS

- [ ] **Step 3: Run full test suite**

Run: `cd scanner && python -m pytest tests/ -v --tb=short`
Expected: all tests PASS

- [ ] **Step 4: Commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add scanner/tests/test_integration.py
git commit -m "test: end-to-end integration test with mocked Telegram and Claude"
```

---

## Summary

8 tasks, ~40 steps total. After Task 7, you'll have a working scanner you can run from the terminal:

```bash
cd scanner
python -m src.cli --config config.yaml -v
```

This produces:
1. `scan_results.json` with all classified triage items
2. A Telegram digest in your Saved Messages (unless `--no-digest`)

**Phase 2** (separate plan): Database push + Next.js Kanban dashboard on Vercel.
**Phase 3** (separate plan): Notion, GitHub, Calendar sources.
**Phase 4** (separate plan): Cron scheduling + deduplication.
