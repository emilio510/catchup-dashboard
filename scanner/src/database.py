from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import asyncpg

from src.models import ScanResult, TriageItem

logger = logging.getLogger(__name__)


def build_scan_insert(result: ScanResult) -> tuple[str, list]:
    query = """
        INSERT INTO scans (sources, dialogs_listed, dialogs_filtered, dialogs_classified, stats, scanned_at)
        VALUES ($1, $2, $3, $4, $5::jsonb, $6)
        RETURNING id
    """
    params = [
        result.sources,
        result.dialogs_listed,
        result.dialogs_filtered,
        result.dialogs_classified,
        json.dumps(result.stats.model_dump()),
        result.scanned_at,
    ]
    return query, params


def build_item_insert(item: TriageItem, scan_id: str) -> tuple[str, list]:
    query = """
        INSERT INTO triage_items (
            scan_id, source, chat_name, chat_type, waiting_person,
            preview, context_summary, draft_reply, priority, status,
            tags, last_message_at, waiting_since, waiting_days,
            chat_id, message_id, scanned_at
        ) VALUES (
            $1, $2, $3, $4, $5,
            $6, $7, $8, $9, $10,
            $11, $12, $13, $14,
            $15, $16, $17
        )
    """
    params = [
        scan_id,
        item.source,
        item.chat_name,
        item.chat_type,
        item.waiting_person,
        item.preview,
        item.context_summary,
        item.draft_reply,
        item.priority,
        item.status,
        item.tags,
        item.last_message_at,
        item.waiting_since,
        item.waiting_days,
        item.chat_id,
        item.message_id,
        datetime.now(timezone.utc),
    ]
    return query, params


def should_reclassify(
    last_message_at: datetime | None,
    previous_scan_at: datetime | None,
    previous_user_status: str | None,
) -> bool:
    if previous_scan_at is None:
        return True
    if last_message_at is None:
        return False
    if previous_user_status == "done":
        return last_message_at > previous_scan_at
    return last_message_at > previous_scan_at


def build_update_scanned_at(item_id: str, new_scan_id: str) -> tuple[str, list]:
    query = """
        UPDATE triage_items
        SET scan_id = $1::uuid, scanned_at = now()
        WHERE id = $2::uuid
    """
    return query, [new_scan_id, item_id]


async def get_previous_items(database_url: str, chat_ids: list[int]) -> dict[int, dict]:
    if not chat_ids:
        return {}
    conn = await asyncpg.connect(database_url)
    try:
        rows = await conn.fetch("""
            SELECT DISTINCT ON (chat_id)
                id, chat_id, scanned_at, user_status, last_message_at
            FROM triage_items
            WHERE chat_id = ANY($1)
            ORDER BY chat_id, scanned_at DESC
        """, chat_ids)
        return {
            row["chat_id"]: {
                "id": str(row["id"]),
                "scanned_at": row["scanned_at"],
                "user_status": row["user_status"],
                "last_message_at": row["last_message_at"],
            }
            for row in rows
        }
    finally:
        await conn.close()


async def delete_calendar_items(database_url: str) -> int:
    conn = await asyncpg.connect(database_url)
    try:
        result = await conn.execute(
            "DELETE FROM triage_items WHERE source = 'calendar'"
        )
        count = int(result.split()[-1])
        if count:
            logger.info("Deleted %d old calendar items", count)
        return count
    finally:
        await conn.close()


async def push_to_database(database_url: str, result: ScanResult) -> str:
    conn = await asyncpg.connect(database_url)
    try:
        async with conn.transaction():
            scan_query, scan_params = build_scan_insert(result)
            scan_id = await conn.fetchval(scan_query, *scan_params)
            for item in result.items:
                item_query, item_params = build_item_insert(item, str(scan_id))
                await conn.execute(item_query, *item_params)
            logger.info("Pushed scan %s with %d items to database", scan_id, len(result.items))
            return str(scan_id)
    finally:
        await conn.close()
