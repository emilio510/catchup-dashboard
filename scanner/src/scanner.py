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
