from __future__ import annotations

import json
import logging
from pathlib import Path

from src.classifier import Classifier
from src.config import ScannerConfig
from src.database import push_to_database
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
                for conv in conversations:
                    prev = previous.get(conv.dialog.chat_id)
                    if prev is None:
                        to_classify.append(conv)
                    else:
                        last_msg = conv.messages[-1].date if conv.messages else None
                        if should_reclassify(last_msg, prev["scanned_at"], prev["user_status"]):
                            to_classify.append(conv)

                logger.info(
                    "Dedup: %d to classify, %d unchanged",
                    len(to_classify), len(conversations) - len(to_classify),
                )
                conversations = to_classify

            if not conversations:
                logger.info("No conversations need reclassification after dedup")
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

            # 4. Get display name for classification
            my_name = self._reader.me_name

            # 5. Classify
            items = await self._classifier.classify_all(conversations, my_name)
            logger.info("Classified %d items", len(items))

            # 6. Sort by priority
            priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
            items.sort(key=lambda i: priority_order.get(i.priority, 99))

            # 7. Build result
            stats = self._compute_stats(items)
            result = ScanResult(
                sources=["telegram"],
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
                text = format_digest(result, self._config.output.dashboard_url)
                chat_id = self._config.output.digest_chat_id or "me"
                await self._reader.send_message(chat_id, text)
                logger.info("Digest sent to chat %s", chat_id)

            return result

        finally:
            await self._reader.disconnect()
