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
