from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.config import (
    ClassificationConfig,
    OutputConfig,
    ScanConfig,
    ScannerConfig,
    TelegramConfig,
)
from src.models import PriorityStats, ScanStats, TriageItem
from src.scanner import Scanner
from src.telegram_reader import ChatMessage, ConversationData, DialogInfo


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_config(tmp_path: Path) -> ScannerConfig:
    json_file = str(tmp_path / "scan_results.json")
    return ScannerConfig(
        scan=ScanConfig(window_days=7, messages_per_chat=20),
        telegram=TelegramConfig(api_id=0, api_hash=""),
        classification=ClassificationConfig(api_key="fake"),
        output=OutputConfig(telegram_digest=False, json_file=json_file),
    )


def _make_conversation() -> ConversationData:
    dialog = DialogInfo(
        chat_id=123456,
        name="Logic Protocol Core",
        is_channel=False,
        is_bot=False,
        last_message_sender_is_me=False,
        last_message_date=datetime(2026, 4, 7, 14, 0, 0, tzinfo=timezone.utc),
    )
    messages = [
        ChatMessage(
            sender_name="Marc",
            sender_id=99,
            text="What about the vault params?",
            date=datetime(2026, 4, 7, 14, 0, 0, tzinfo=timezone.utc),
            message_id=1,
            is_me=False,
        )
    ]
    return ConversationData(dialog=dialog, messages=messages, chat_type="group")


def _make_triage_item() -> TriageItem:
    return TriageItem(
        source="telegram",
        chat_name="Logic Protocol Core",
        chat_type="group",
        priority="P0",
        status="READ_NO_REPLY",
        waiting_person="Marc",
        waiting_since=datetime(2026, 4, 7, 14, 0, 0, tzinfo=timezone.utc),
        waiting_days=3,
        tags=["deal blocker"],
        context_summary="Marc asking about vault parameters",
        draft_reply="Hey Marc, here are the params...",
        preview="What about the vault params?",
    )


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scanner_run_full_pipeline(tmp_path: Path) -> None:
    """Full Scanner.run() pipeline with TelegramReader and Classifier mocked."""
    config = _make_config(tmp_path)
    conversation = _make_conversation()
    expected_item = _make_triage_item()

    fake_me = MagicMock()
    fake_me.first_name = "Emile"
    fake_me.id = 42

    with (
        patch("src.scanner.TelegramReader") as MockReader,
        patch("src.scanner.Classifier") as MockClassifier,
    ):
        # --- TelegramReader mock setup ---
        reader_instance = MagicMock()
        reader_instance.connect = AsyncMock()
        reader_instance.disconnect = AsyncMock()
        # read_all returns (conversations, total_dialogs, filtered_count)
        reader_instance.read_all = AsyncMock(return_value=([conversation], 5, 2))
        # _client.get_me() used to get display name
        reader_instance._client = MagicMock()
        reader_instance._client.get_me = AsyncMock(return_value=fake_me)
        MockReader.return_value = reader_instance

        # --- Classifier mock setup ---
        classifier_instance = MagicMock()
        classifier_instance.classify_all = AsyncMock(return_value=[expected_item])
        MockClassifier.return_value = classifier_instance

        scanner = Scanner(config)
        result = await scanner.run()

    # Verify connect/disconnect lifecycle
    reader_instance.connect.assert_awaited_once()
    reader_instance.disconnect.assert_awaited_once()

    # Verify read_all was called
    reader_instance.read_all.assert_awaited_once()

    # Verify classify_all was called with the conversation and user name
    classifier_instance.classify_all.assert_awaited_once_with([conversation], "Emile")

    # Verify result shape
    assert result.sources == ["telegram"]
    assert result.dialogs_listed == 5
    assert result.dialogs_classified == 1
    assert len(result.items) == 1

    item = result.items[0]
    assert item.chat_name == "Logic Protocol Core"
    assert item.priority == "P0"
    assert item.status == "READ_NO_REPLY"
    assert item.waiting_person == "Marc"
    assert item.waiting_days == 3
    assert "deal blocker" in item.tags
    assert item.preview == "What about the vault params?"

    # Verify stats
    assert result.stats.total == 1
    assert result.stats.by_priority.P0 == 1
    assert result.stats.by_priority.P1 == 0
    assert result.stats.by_status["READ_NO_REPLY"] == 1

    # Verify JSON output was written
    json_path = Path(config.output.json_file)
    assert json_path.exists(), "JSON output file should have been written"

    written = json.loads(json_path.read_text())
    assert written["stats"]["total"] == 1
    assert written["dialogs_listed"] == 5
    assert len(written["items"]) == 1
    assert written["items"][0]["chat_name"] == "Logic Protocol Core"
    assert written["items"][0]["priority"] == "P0"


@pytest.mark.asyncio
async def test_scanner_run_no_conversations(tmp_path: Path) -> None:
    """Scanner.run() returns empty result when no conversations pass filtering."""
    config = _make_config(tmp_path)

    with (
        patch("src.scanner.TelegramReader") as MockReader,
        patch("src.scanner.Classifier") as MockClassifier,
    ):
        reader_instance = MagicMock()
        reader_instance.connect = AsyncMock()
        reader_instance.disconnect = AsyncMock()
        # No conversations after filtering
        reader_instance.read_all = AsyncMock(return_value=([], 10, 10))
        reader_instance._client = MagicMock()
        MockReader.return_value = reader_instance

        classifier_instance = MagicMock()
        classifier_instance.classify_all = AsyncMock(return_value=[])
        MockClassifier.return_value = classifier_instance

        scanner = Scanner(config)
        result = await scanner.run()

    # Classifier should NOT be called when there are no conversations
    classifier_instance.classify_all.assert_not_awaited()

    assert result.items == []
    assert result.stats.total == 0
    assert result.dialogs_listed == 10
    assert result.dialogs_classified == 0


@pytest.mark.asyncio
async def test_scanner_run_priority_sorting(tmp_path: Path) -> None:
    """Scanner.run() sorts items by priority (P0 first)."""
    config = _make_config(tmp_path)

    p2_item = TriageItem(
        source="telegram",
        chat_name="Low Priority Chat",
        chat_type="dm",
        priority="P2",
        status="READ_NO_REPLY",
        preview="meh",
    )
    p0_item = TriageItem(
        source="telegram",
        chat_name="Urgent Chat",
        chat_type="dm",
        priority="P0",
        status="NEW",
        preview="urgent!",
    )
    p1_item = TriageItem(
        source="telegram",
        chat_name="Medium Chat",
        chat_type="group",
        priority="P1",
        status="MONITORING",
        preview="medium",
    )

    fake_me = MagicMock()
    fake_me.first_name = "Emile"
    fake_me.id = 42

    conversation = _make_conversation()

    with (
        patch("src.scanner.TelegramReader") as MockReader,
        patch("src.scanner.Classifier") as MockClassifier,
    ):
        reader_instance = MagicMock()
        reader_instance.connect = AsyncMock()
        reader_instance.disconnect = AsyncMock()
        reader_instance.read_all = AsyncMock(return_value=([conversation], 3, 0))
        reader_instance._client = MagicMock()
        reader_instance._client.get_me = AsyncMock(return_value=fake_me)
        MockReader.return_value = reader_instance

        classifier_instance = MagicMock()
        # Return items in wrong order — scanner should sort them
        classifier_instance.classify_all = AsyncMock(
            return_value=[p2_item, p0_item, p1_item]
        )
        MockClassifier.return_value = classifier_instance

        scanner = Scanner(config)
        result = await scanner.run()

    priorities = [item.priority for item in result.items]
    assert priorities == ["P0", "P1", "P2"], f"Expected sorted priorities, got {priorities}"
