from __future__ import annotations

import asyncio
import logging
import uuid as uuid_mod
from datetime import datetime, timedelta, timezone

import asyncpg
import httpx

from src.config import ScannerConfig

logger = logging.getLogger(__name__)


def should_remind(
    priority: str,
    waiting_since: datetime | None,
    last_reminded_at: datetime | None,
    thresholds: dict[str, int | None],
    now: datetime,
) -> bool:
    if waiting_since is None:
        return False

    threshold_hours = thresholds.get(priority)
    if threshold_hours is None:
        return False

    threshold = timedelta(hours=threshold_hours)
    overdue = now - waiting_since

    if overdue < threshold:
        return False

    if last_reminded_at is not None:
        since_last_reminder = now - last_reminded_at
        if since_last_reminder < threshold:
            return False

    return True


def format_reminder(
    chat_name: str,
    priority: str,
    waiting_person: str | None,
    hours_overdue: float,
    preview: str | None,
) -> str:
    person = waiting_person or "Someone"
    hours_int = int(hours_overdue)
    lines = [
        f"Reminder: {priority} item overdue ({hours_int}h)",
        f"Chat: {chat_name}",
        f"Waiting: {person}",
    ]
    if preview:
        lines.append(f"Preview: {preview[:100]}")
    return "\n".join(lines)


async def find_overdue_items(
    database_url: str,
    thresholds: dict[str, int | None],
) -> list[dict]:
    now = datetime.now(timezone.utc)
    conn = await asyncpg.connect(database_url)
    try:
        rows = await conn.fetch("""
            SELECT DISTINCT ON (COALESCE(chat_id::text, id::text))
                id, chat_name, priority, waiting_person, waiting_since,
                preview, last_reminded_at
            FROM triage_items
            WHERE user_status = 'open'
              AND source = 'telegram'
              AND waiting_since IS NOT NULL
              AND chat_id IS NOT NULL
            ORDER BY COALESCE(chat_id::text, id::text), scanned_at DESC
        """)

        overdue = []
        for row in rows:
            if should_remind(
                row["priority"],
                row["waiting_since"],
                row["last_reminded_at"],
                thresholds,
                now,
            ):
                hours_overdue = (now - row["waiting_since"]).total_seconds() / 3600
                overdue.append({
                    "id": str(row["id"]),
                    "chat_name": row["chat_name"],
                    "priority": row["priority"],
                    "waiting_person": row["waiting_person"],
                    "hours_overdue": hours_overdue,
                    "preview": row["preview"],
                })
        return overdue
    finally:
        await conn.close()


async def mark_reminded(database_url: str, item_ids: list[str]) -> None:
    if not item_ids:
        return
    conn = await asyncpg.connect(database_url)
    try:
        await conn.execute("""
            UPDATE triage_items
            SET last_reminded_at = now()
            WHERE id = ANY($1::uuid[])
        """, item_ids)
    finally:
        await conn.close()


async def send_reminders(config: ScannerConfig) -> int:
    if not config.output.database_url:
        logger.warning("No DATABASE_URL configured")
        return 0

    bot_token = config.output.digest_bot_token
    chat_id = config.output.digest_chat_id
    if not bot_token or not chat_id:
        logger.warning("No bot token or chat ID configured for escalation")
        return 0

    thresholds = config.escalation.model_dump()
    now = datetime.now(timezone.utc)

    conn = await asyncpg.connect(config.output.database_url, timeout=30)
    try:
        async with conn.transaction():
            # Claim rows atomically; FOR UPDATE SKIP LOCKED prevents concurrent runs
            rows = await conn.fetch("""
                SELECT id, chat_name, priority, waiting_person, waiting_since,
                       preview, last_reminded_at
                FROM triage_items
                WHERE user_status = 'open'
                  AND source = 'telegram'
                  AND waiting_since IS NOT NULL
                  AND chat_id IS NOT NULL
                ORDER BY scanned_at DESC
                FOR UPDATE SKIP LOCKED
            """)

            # DISTINCT ON chat_name + should_remind filter (done in Python because
            # DISTINCT ON is incompatible with FOR UPDATE)
            seen_chats: set[str] = set()
            overdue: list[dict] = []
            for row in rows:
                chat_name = row["chat_name"]
                if chat_name in seen_chats:
                    continue
                seen_chats.add(chat_name)

                if should_remind(
                    row["priority"],
                    row["waiting_since"],
                    row["last_reminded_at"],
                    thresholds,
                    now,
                ):
                    hours_overdue = (now - row["waiting_since"]).total_seconds() / 3600
                    overdue.append({
                        "id": str(row["id"]),
                        "chat_name": chat_name,
                        "priority": row["priority"],
                        "waiting_person": row["waiting_person"],
                        "hours_overdue": hours_overdue,
                        "preview": row["preview"],
                    })

            if not overdue:
                logger.debug("No overdue items")
                return 0

            logger.info("Found %d overdue items to remind", len(overdue))

            sent_ids: list[str] = []
            async with httpx.AsyncClient(timeout=10.0) as http:
                for item in overdue:
                    text = format_reminder(
                        chat_name=item["chat_name"],
                        priority=item["priority"],
                        waiting_person=item["waiting_person"],
                        hours_overdue=item["hours_overdue"],
                        preview=item["preview"],
                    )
                    try:
                        resp = await http.post(
                            f"https://api.telegram.org/bot{bot_token}/sendMessage",
                            json={"chat_id": chat_id, "text": text},
                        )
                        if resp.is_success:
                            sent_ids.append(item["id"])
                            logger.info("Sent reminder for %s", item["chat_name"])
                        else:
                            logger.error(
                                "Failed to send reminder for %s: status %d",
                                item["chat_name"],
                                resp.status_code,
                            )
                    except httpx.HTTPError:
                        logger.error("HTTP error sending reminder for %s", item["chat_name"])

            # Mark reminded within the same transaction to keep reads and writes atomic
            if sent_ids:
                await conn.execute("""
                    UPDATE triage_items
                    SET last_reminded_at = now()
                    WHERE id = ANY($1::uuid[])
                """, [uuid_mod.UUID(id_str) for id_str in sent_ids])

            return len(sent_ids)
    finally:
        await conn.close()


async def async_main() -> None:
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Send escalation reminders for overdue items")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.DEBUG if args.verbose else logging.INFO,
    )

    config = ScannerConfig.from_yaml(args.config)
    count = await send_reminders(config)
    if count:
        print(f"Sent {count} reminders")


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
