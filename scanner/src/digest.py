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
