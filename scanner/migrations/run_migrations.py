"""Run all pending migrations against the database."""
import asyncio
import os

import asyncpg
from dotenv import load_dotenv

load_dotenv()


async def main():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        await conn.execute(
            "ALTER TABLE triage_items ADD COLUMN IF NOT EXISTS last_reminded_at TIMESTAMPTZ"
        )
        print("002: last_reminded_at column added")

        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_triage_chat_id_scanned ON triage_items (chat_id, scanned_at DESC)"
        )
        print("003: chat_id+scanned_at index created")

        await conn.execute(
            "ALTER TABLE triage_items ADD COLUMN IF NOT EXISTS source_id TEXT"
        )
        print("004: source_id column added")

        await conn.execute("DROP INDEX IF EXISTS idx_triage_dedup")
        await conn.execute(
            "CREATE INDEX idx_triage_dedup ON triage_items (COALESCE(chat_id::text, source_id, id::text), scanned_at DESC)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_triage_source_id ON triage_items (source_id, scanned_at DESC) WHERE source_id IS NOT NULL"
        )
        print("005: dedup index updated, source_id index added")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
