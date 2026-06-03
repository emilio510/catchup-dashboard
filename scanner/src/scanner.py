from __future__ import annotations

import json
import logging
from pathlib import Path

from src.notion_scanner import (
    scan_notion,
    format_notion_items_for_classifier,
    comments_to_triage_items,
)
from src.classifier import Classifier
from src.config import ScannerConfig
from src.database import get_previous_notion_items, push_to_database
from src.digest import format_digest
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
                    dialogs_filtered=filtered_count,
                    dialogs_classified=0,
                    items=[],
                    stats=stats,
                )

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
                prev_context_by_name: dict[str, dict] = {}
                for conv in conversations:
                    prev = previous.get(conv.dialog.chat_id)
                    if prev is None:
                        to_classify.append(conv)
                    else:
                        # Use dialog.last_message_date (from iter_dialogs) -- this is
                        # always the actual latest message, unlike conv.messages[-1].date
                        # which is limited by messages_per_chat and may be days old.
                        last_msg = conv.dialog.last_message_date
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

            # 3c. Fetch Notion items (if enabled)
            notion_rule_items: list[TriageItem] = []
            notion_mention_groups: dict[str, dict] = {}
            if self._config.notion.enabled:
                try:
                    notion_rule_items, notion_mention_groups = await scan_notion(self._config)
                    if notion_mention_groups:
                        self._classifier.notion_context = format_notion_items_for_classifier(notion_mention_groups)
                    logger.info(
                        "Notion: %d assignments, %d pages with mentions",
                        len(notion_rule_items), len(notion_mention_groups),
                    )
                except Exception:
                    logger.exception("Failed to fetch Notion items (continuing without)")

            # Dedup Notion items against previous scan
            if self._config.output.database_url and (notion_rule_items or notion_mention_groups):
                try:
                    all_notion_source_ids = [
                        item.source_id for item in notion_rule_items if item.source_id
                    ] + [
                        group["page_id"] for group in notion_mention_groups.values()
                    ]
                    if all_notion_source_ids:
                        prev_notion = await get_previous_notion_items(
                            self._config.output.database_url, all_notion_source_ids
                        )
                        # Filter out items that haven't changed (still open, same preview)
                        notion_rule_items = [
                            item for item in notion_rule_items
                            if item.source_id not in prev_notion
                            or prev_notion[item.source_id]["user_status"] == "done"
                            or prev_notion[item.source_id]["preview"] != item.preview
                        ]
                        # Filter mention groups to only pages with new/changed comments
                        notion_mention_groups = {
                            title: group for title, group in notion_mention_groups.items()
                            if group["page_id"] not in prev_notion
                            or prev_notion[group["page_id"]]["user_status"] == "done"
                            or prev_notion[group["page_id"]]["preview"] != (
                                f"{group['comments'][0]['created_by_name']}: {group['comments'][0]['text']}"[:200]
                                if group["comments"] else ""
                            )
                        }
                except Exception:
                    logger.exception("Failed to dedup Notion items, including all")

            if not conversations:
                logger.info("No conversations need reclassification after dedup")
                sources = ["telegram"]
                if notion_rule_items or notion_mention_groups:
                    sources.append("notion")
                all_items = notion_rule_items
                if notion_mention_groups:
                    all_items.extend(comments_to_triage_items(notion_mention_groups))
                stats = self._compute_stats(all_items)
                result = ScanResult(
                    sources=sources,
                    dialogs_listed=total_dialogs,
                    dialogs_filtered=filtered_count,
                    dialogs_classified=0,
                    items=all_items,
                    stats=stats,
                )

                # Output JSON
                output_path = Path(self._config.output.json_file)
                output_path.write_text(result.model_dump_json(indent=2))
                logger.info("Results written to %s", output_path)

                # Push to database
                if self._config.output.database_url and all_items:
                    try:
                        await push_to_database(self._config.output.database_url, result)
                    except Exception:
                        logger.exception("Failed to push to database")

                return result

            # 4. Get display name for classification
            my_name = self._reader.me_name

            # 5. Classify
            items = await self._classifier.classify_all(conversations, my_name, previous_context)
            logger.info("Classified %d items", len(items))

            # 6. Add notion items + sort by priority
            items.extend(notion_rule_items)
            if notion_mention_groups:
                items.extend(comments_to_triage_items(notion_mention_groups))
            priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
            items.sort(key=lambda i: priority_order.get(i.priority, 99))

            # 7. Build result
            sources = ["telegram"]
            if notion_rule_items or notion_mention_groups:
                sources.append("notion")
            stats = self._compute_stats(items)
            result = ScanResult(
                sources=sources,
                dialogs_listed=total_dialogs,
                dialogs_filtered=filtered_count,
                dialogs_classified=len(conversations),
                items=items,
                stats=stats,
            )

            # 8. Output JSON
            output_path = Path(self._config.output.json_file)
            output_path.write_text(result.model_dump_json(indent=2))
            logger.info("Results written to %s", output_path)

            # 9. Push to database
            if self._config.output.database_url:
                try:
                    await push_to_database(self._config.output.database_url, result)
                except Exception:
                    logger.exception("Failed to push to database (scan results still saved to JSON)")

            # 10. Send Telegram digest
            if self._config.output.telegram_digest:
                try:
                    text = format_digest(result, self._config.output.dashboard_url)
                    bot_token = self._config.output.digest_bot_token
                    chat_id = self._config.output.digest_chat_id

                    if bot_token and chat_id:
                        import httpx
                        async with httpx.AsyncClient(timeout=10.0) as http:
                            resp = await http.post(
                                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                                json={"chat_id": chat_id, "text": text},
                            )
                            if resp.is_success:
                                logger.info("Digest sent via bot to chat %s", chat_id)
                            else:
                                logger.error("Bot API error: %s", resp.text)
                    else:
                        await self._reader.send_message(chat_id or "me", text)
                        logger.info("Digest sent to chat %s", chat_id or "me")
                except Exception:
                    logger.exception("Failed to send digest (scan results still saved)")

            return result

        finally:
            await self._reader.disconnect()
