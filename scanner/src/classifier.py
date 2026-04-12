from __future__ import annotations

import asyncio
import json
import logging
import re
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


def build_classification_prompt(
    conversations: list[ConversationData],
    my_display_name: str,
    user_context: str,
    calendar_context: str = "",
    previous_context: dict[str, dict] | None = None,
    notion_context: str = "",
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

    if notion_context:
        parts.append(notion_context)
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
        # Claude sometimes wraps JSON in markdown code blocks
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response_text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
            except json.JSONDecodeError:
                logger.error("Failed to parse classifier JSON (even after stripping markdown)")
                return []
        else:
            logger.error("Failed to parse classifier JSON response: %s", response_text[:200])
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
        self.calendar_context: str = ""
        self.notion_context: str = ""

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
            notion_context=self.notion_context,
        )

        response = None
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self._client.messages.create(
                    model=self._config.classification.model,
                    max_tokens=self._config.classification.max_tokens,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                )
                break
            except (anthropic.OverloadedError, anthropic.RateLimitError) as exc:
                if attempt == max_retries - 1:
                    logger.error("API failed after %d retries: %s", max_retries, exc)
                    return []
                wait = 2 ** (attempt + 1)
                logger.warning("API error (attempt %d/%d), retrying in %ds: %s", attempt + 1, max_retries, wait, exc)
                await asyncio.sleep(wait)
            except Exception as exc:
                logger.error("Unexpected API error: %s", exc)
                return []

        if response is None or not response.content or response.content[0].type != "text":
            logger.error("Unexpected response: stop_reason=%s", getattr(response, 'stop_reason', 'none'))
            return []

        response_text = response.content[0].text

        # Parse JSON, handling markdown code blocks
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response_text, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                except json.JSONDecodeError:
                    logger.error("Failed to parse classifier JSON (even after stripping markdown): %s", response_text[:300])
                    return []
            else:
                logger.error("Failed to parse classifier JSON response: %s", response_text[:300])
                return []

        if not isinstance(data, list):
            data = [data]

        # Build lookup from chat_name -> conversation metadata
        conv_by_name: dict[str, ConversationData] = {}
        for c in conversations:
            conv_by_name[c.dialog.name] = c

        items: list[TriageItem] = []
        for entry in data:
            try:
                chat_name = entry.get("chat_name", "")
                conv = conv_by_name.get(chat_name)
                chat_id = conv.dialog.chat_id if conv else 0
                chat_type = conv.chat_type if conv else "dm"
                last_msg_id = conv.messages[-1].message_id if conv and conv.messages else 0

                waiting_since = None
                if entry.get("waiting_since"):
                    try:
                        waiting_since = datetime.fromisoformat(
                            entry["waiting_since"].replace("Z", "+00:00")
                        )
                    except (ValueError, TypeError):
                        pass

                item = TriageItem(
                    source="telegram",
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
                    message_id=last_msg_id,
                )
                items.append(item)
            except Exception:
                logger.exception("Failed to parse classification entry: %s", entry)

        return items

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
