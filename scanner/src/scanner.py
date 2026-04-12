from __future__ import annotations

import json
import logging
from pathlib import Path

from src.calendar_scanner import CalendarEvent, events_to_triage_items, fetch_calendar_events, find_related_chat_names, format_events_for_classifier
from src.classifier import Classifier
from src.config import ScannerConfig
from src.database import delete_calendar_items, push_to_database
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

            # 3b. Fetch calendar events (if enabled) -- before dedup early-return
            # so calendar cards are always created
            calendar_events: list[CalendarEvent] = []
            calendar_items: list[TriageItem] = []
            if self._config.calendar.enabled:
                try:
                    calendar_events = await fetch_calendar_events(
                        credentials_path=Path(self._config.calendar.credentials_path),
                        token_path=Path(self._config.calendar.token_path),
                        days_ahead=self._config.calendar.days_ahead,
                    )
                    self._classifier.calendar_context = format_events_for_classifier(calendar_events)
                    calendar_items = events_to_triage_items(calendar_events)
                    logger.info("Calendar: %d events -> %d triage items", len(calendar_events), len(calendar_items))

                    if calendar_events and conversations:
                        all_chat_names = [c.dialog.name for c in conversations]
                        related = find_related_chat_names(calendar_events, all_chat_names)
                        if related:
                            logger.info("Calendar: %d chats related to upcoming events: %s", len(related), related)
                except Exception:
                    logger.exception("Failed to fetch calendar events (continuing without)")

            if not conversations:
                logger.info("No conversations need reclassification after dedup")
                # Still include calendar items even when no Telegram chats need reclassifying
                sources = ["telegram"]
                if calendar_items:
                    sources.append("calendar")
                all_items = calendar_items
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

                # Push to database (calendar items only)
                if self._config.output.database_url and all_items:
                    if calendar_items:
                        try:
                            await delete_calendar_items(self._config.output.database_url)
                        except Exception:
                            logger.exception("Failed to delete old calendar items")
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

            # 6. Add calendar items + sort by priority
            items.extend(calendar_items)
            priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
            items.sort(key=lambda i: priority_order.get(i.priority, 99))

            # 7. Build result
            sources = ["telegram"]
            if calendar_events:
                sources.append("calendar")
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
                if calendar_items:
                    try:
                        await delete_calendar_items(self._config.output.database_url)
                    except Exception:
                        logger.exception("Failed to delete old calendar items")
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
