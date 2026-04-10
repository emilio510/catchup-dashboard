from __future__ import annotations

import asyncio
import logging

import asyncpg
from telethon import TelegramClient

from src.config import ScannerConfig

logger = logging.getLogger(__name__)


def build_fetch_pending_query() -> str:
    return """
        SELECT pr.id, pr.chat_id, pr.message_text, pr.triage_item_id
        FROM pending_replies pr
        WHERE pr.status = 'pending'
        ORDER BY pr.created_at ASC
        LIMIT 10
    """


def build_mark_sent_query(reply_id: str) -> tuple[str, list]:
    query = """
        UPDATE pending_replies
        SET status = 'sent', sent_at = now()
        WHERE id = $1::uuid
    """
    return query, [reply_id]


def build_mark_failed_query(reply_id: str, error: str) -> tuple[str, list]:
    query = """
        UPDATE pending_replies
        SET status = 'failed', error = $1
        WHERE id = $2::uuid
    """
    return query, [error, reply_id]


async def process_pending_replies(config: ScannerConfig) -> int:
    if not config.output.database_url:
        logger.warning("No DATABASE_URL configured, skipping sender")
        return 0

    conn = await asyncpg.connect(config.output.database_url)
    try:
        rows = await conn.fetch(build_fetch_pending_query())
        if not rows:
            logger.debug("No pending replies")
            return 0

        logger.info("Found %d pending replies", len(rows))

        client = TelegramClient(
            config.telegram.session_name,
            config.telegram.api_id,
            config.telegram.api_hash,
        )
        await client.start()

        try:
            sent_count = 0
            for row in rows:
                reply_id = str(row["id"])
                chat_id = row["chat_id"]
                text = row["message_text"]

                try:
                    await client.send_message(chat_id, text)
                    mark_query, mark_params = build_mark_sent_query(reply_id)
                    await conn.execute(mark_query, *mark_params)

                    await conn.execute(
                        "UPDATE triage_items SET user_status = 'done', user_status_at = now() WHERE id = $1::uuid",
                        row["triage_item_id"],
                    )

                    sent_count += 1
                    logger.info("Sent reply to chat %s", chat_id)
                except Exception:
                    logger.exception("Failed to send reply %s", reply_id)
                    fail_query, fail_params = build_mark_failed_query(reply_id, str(row))
                    await conn.execute(fail_query, *fail_params)

            return sent_count
        finally:
            await client.disconnect()
    finally:
        await conn.close()


async def async_main() -> None:
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Send queued Telegram replies")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.DEBUG if args.verbose else logging.INFO,
    )

    config = ScannerConfig.from_yaml(args.config)
    count = await process_pending_replies(config)
    if count:
        print(f"Sent {count} replies")


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
