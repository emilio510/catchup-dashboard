# Reply from Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable sending Telegram replies directly from the dashboard by editing AI draft replies and clicking Send. Messages are queued in Postgres and sent by a lightweight sender script polling every 2 minutes via Telethon.

**Architecture:** Dashboard writes pending replies to a `pending_replies` table in Postgres. A new `sender.py` script connects to Telegram via Telethon, polls the DB for unsent replies, sends them, marks them as sent, and auto-marks the triage item as "done". Runs as a separate launchd cron every 2 minutes.

**Tech Stack:** Postgres (pending_replies table), Next.js Server Actions (queue reply), Python asyncpg + Telethon (sender), macOS launchd (2-min cron)

---

## File Structure

```
schema.sql                          # MODIFY: add pending_replies table

scanner/
  src/
    sender.py                       # CREATE: poll DB, send via Telethon, mark sent
  cron/
    run-sender.sh                   # CREATE: wrapper script for sender cron
    catchup-sender.plist            # CREATE: launchd plist (2-min interval)
  tests/
    test_sender.py                  # CREATE: tests for sender logic

dashboard/
  lib/
    db.ts                           # MODIFY: add queueReply function
  app/
    actions.ts                      # MODIFY: add sendReply server action
  components/
    card-detail.tsx                 # MODIFY: add editable textarea + Send button
```

---

### Task 1: Database Schema for Pending Replies

**Files:**
- Modify: `schema.sql`

- [ ] **Step 1: Add pending_replies table to schema.sql**

Append to the end of `schema.sql`:

```sql
CREATE TABLE pending_replies (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  triage_item_id  UUID NOT NULL REFERENCES triage_items(id),
  chat_id         BIGINT NOT NULL,
  message_text    TEXT NOT NULL,
  status          TEXT NOT NULL DEFAULT 'pending',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  sent_at         TIMESTAMPTZ,
  error           TEXT
);

CREATE INDEX idx_pending_replies_status ON pending_replies(status);
```

- [ ] **Step 2: Run migration on Neon**

Use the Neon SQL Editor or Node.js to run just the new table creation:

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && node -e "
const { neon } = require('@neondatabase/serverless');
const sql = neon(process.env.DATABASE_URL);
(async () => {
  await sql\`CREATE TABLE IF NOT EXISTS pending_replies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    triage_item_id UUID NOT NULL REFERENCES triage_items(id),
    chat_id BIGINT NOT NULL,
    message_text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    sent_at TIMESTAMPTZ,
    error TEXT
  )\`;
  await sql\`CREATE INDEX IF NOT EXISTS idx_pending_replies_status ON pending_replies(status)\`;
  console.log('pending_replies table created');
})();
"
```

- [ ] **Step 3: Commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add schema.sql
git commit -m "feat: add pending_replies table for queued Telegram messages"
```

---

### Task 2: Dashboard -- Editable Draft Reply + Send Button

**Files:**
- Modify: `dashboard/lib/db.ts`
- Modify: `dashboard/app/actions.ts`
- Modify: `dashboard/components/card-detail.tsx`

- [ ] **Step 1: Add queueReply to db.ts**

Add to `dashboard/lib/db.ts`:

```typescript
export async function queueReply(
  triageItemId: string,
  chatId: number,
  messageText: string
): Promise<void> {
  const sql = getDb();
  await sql`
    INSERT INTO pending_replies (triage_item_id, chat_id, message_text)
    VALUES (${triageItemId}::uuid, ${chatId}, ${messageText})
  `;
}
```

- [ ] **Step 2: Add sendReply server action to actions.ts**

Add to `dashboard/app/actions.ts`:

```typescript
import { updateItemStatus, queueReply } from "@/lib/db";

export async function sendReply(itemId: string, chatId: number, messageText: string): Promise<void> {
  validateItemId(itemId);
  if (!messageText.trim()) {
    throw new Error("Message cannot be empty");
  }
  await queueReply(itemId, chatId, messageText);
  await updateItemStatus(itemId, "done");
  revalidatePath("/");
}
```

Update the import at the top to include `queueReply`.

- [ ] **Step 3: Update card-detail.tsx with editable textarea and Send button**

Replace the entire `dashboard/components/card-detail.tsx` with:

```typescript
"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import type { TriageItem } from "@/lib/types";
import { markItemDone, snoozeItem, sendReply } from "@/app/actions";

interface CardDetailProps {
  item: TriageItem;
}

export function CardDetail({ item }: CardDetailProps) {
  const [isPending, startTransition] = useTransition();
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [replyText, setReplyText] = useState(item.draft_reply ?? "");
  const [sent, setSent] = useState(false);
  const router = useRouter();

  function handleAction(action: (id: string) => Promise<void>, actionName: string) {
    setPendingAction(actionName);
    startTransition(async () => {
      await action(item.id);
      router.refresh();
      setPendingAction(null);
    });
  }

  function handleSend() {
    if (!replyText.trim() || !item.chat_id) return;
    setPendingAction("send");
    startTransition(async () => {
      await sendReply(item.id, item.chat_id!, replyText);
      setSent(true);
      router.refresh();
      setPendingAction(null);
    });
  }

  return (
    <div className="mt-3 pt-3 border-t border-[#30363d]">
      {item.context_summary && (
        <p className="text-[#8b949e] text-xs mb-2">{item.context_summary}</p>
      )}
      {!sent && (
        <div className="bg-[#0d1117] rounded p-2 mb-3">
          <div className="text-[10px] text-[#8b949e] mb-1 uppercase tracking-wide">
            {item.draft_reply ? "Edit & send reply" : "Write a reply"}
          </div>
          <textarea
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            rows={3}
            className="w-full bg-[#161b22] border border-[#30363d] rounded px-2 py-1.5 text-xs text-[#e6edf3] placeholder-[#8b949e] outline-none focus:border-[#388bfd] resize-y"
            placeholder="Type your reply..."
          />
        </div>
      )}
      {sent && (
        <div className="bg-[#238636]/20 border border-[#238636]/40 rounded p-2 mb-3">
          <p className="text-[10px] text-[#3fb950]">Reply queued -- will be sent within 2 minutes</p>
        </div>
      )}
      <div className="flex gap-2">
        {!sent && item.chat_id && (
          <button
            onClick={handleSend}
            disabled={isPending || !replyText.trim()}
            className="px-2 py-1 text-[10px] rounded bg-[#1f6feb] hover:bg-[#388bfd] text-white disabled:opacity-50"
          >
            {pendingAction === "send" ? "Queuing..." : "Send reply"}
          </button>
        )}
        <button
          onClick={() => handleAction(markItemDone, "done")}
          disabled={isPending}
          className="px-2 py-1 text-[10px] rounded bg-[#238636] hover:bg-[#2ea043] text-white disabled:opacity-50"
        >
          {pendingAction === "done" ? "..." : "Done"}
        </button>
        <button
          onClick={() => handleAction(snoozeItem, "snooze")}
          disabled={isPending}
          className="px-2 py-1 text-[10px] rounded bg-[#30363d] hover:bg-[#484f58] text-[#8b949e] disabled:opacity-50"
        >
          {pendingAction === "snooze" ? "..." : "Snooze"}
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run type check**

```bash
cd dashboard && npx tsc --noEmit --skipLibCheck
```

- [ ] **Step 5: Commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/lib/db.ts dashboard/app/actions.ts dashboard/components/card-detail.tsx
git commit -m "feat: editable draft reply with Send button, queues to pending_replies"
```

---

### Task 3: Sender Script (Python)

**Files:**
- Create: `scanner/src/sender.py`
- Create: `scanner/tests/test_sender.py`

- [ ] **Step 1: Write failing tests**

```python
# scanner/tests/test_sender.py
from datetime import datetime, timezone
from src.sender import build_fetch_pending_query, build_mark_sent_query, build_mark_failed_query


def test_build_fetch_pending_query():
    query = build_fetch_pending_query()
    assert "SELECT" in query
    assert "pending_replies" in query
    assert "status = 'pending'" in query


def test_build_mark_sent_query():
    query, params = build_mark_sent_query("reply-uuid")
    assert "UPDATE pending_replies" in query
    assert "sent" in query
    assert params[0] == "reply-uuid"


def test_build_mark_failed_query():
    query, params = build_mark_failed_query("reply-uuid", "Connection error")
    assert "UPDATE pending_replies" in query
    assert "failed" in query
    assert params[0] == "Connection error"
    assert params[1] == "reply-uuid"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd scanner && .venv/bin/python -m pytest tests/test_sender.py -v`

- [ ] **Step 3: Implement sender.py**

```python
# scanner/src/sender.py
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

        # Connect to Telegram
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

                    # Also mark the triage item as done
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd scanner && .venv/bin/python -m pytest tests/test_sender.py -v`

- [ ] **Step 5: Run full test suite**

Run: `cd scanner && .venv/bin/python -m pytest tests/ -v`

- [ ] **Step 6: Commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add scanner/src/sender.py scanner/tests/test_sender.py
git commit -m "feat: sender script -- polls pending_replies, sends via Telethon"
```

---

### Task 4: Sender Cron + Deploy

**Files:**
- Create: `scanner/cron/run-sender.sh`
- Create: `scanner/cron/catchup-sender.plist`

- [ ] **Step 1: Create sender wrapper script**

```bash
#!/bin/bash
# scanner/cron/run-sender.sh
SCANNER_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCANNER_DIR" || exit 1
"$SCANNER_DIR/.venv/bin/python" -m src.sender --config config.yaml 2>&1 >> "$SCANNER_DIR/cron/sender.log"
```

Make executable:
```bash
chmod +x scanner/cron/run-sender.sh
```

- [ ] **Step 2: Create launchd plist (2-min interval)**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.akgemilio.catchup-sender</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/akgemilio/Projects/catchup-dashboard/scanner/cron/run-sender.sh</string>
    </array>
    <key>StartInterval</key>
    <integer>120</integer>
    <key>StandardOutPath</key>
    <string>/Users/akgemilio/Projects/catchup-dashboard/scanner/cron/sender-launchd-stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/akgemilio/Projects/catchup-dashboard/scanner/cron/sender-launchd-stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
    </dict>
</dict>
</plist>
```

- [ ] **Step 3: Install the launchd job**

```bash
cp scanner/cron/catchup-sender.plist ~/Library/LaunchAgents/com.akgemilio.catchup-sender.plist
launchctl load ~/Library/LaunchAgents/com.akgemilio.catchup-sender.plist
launchctl list | grep catchup-sender
```

- [ ] **Step 4: Deploy dashboard**

```bash
cd dashboard && vercel --prod
```

- [ ] **Step 5: Push to GitHub**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add scanner/cron/run-sender.sh scanner/cron/catchup-sender.plist
git commit -m "feat: sender cron -- polls every 2 min for queued replies"
git push
```

- [ ] **Step 6: Test end-to-end**

1. Open dashboard, expand a card, edit the draft, click "Send reply"
2. Verify the card shows "Reply queued" and marks as done
3. Wait up to 2 minutes
4. Check Telegram -- the message should appear from your account in the chat
5. Check `scanner/cron/sender.log` for the send confirmation

---

## Summary

4 tasks:
1. **DB schema** -- `pending_replies` table
2. **Dashboard UI** -- editable textarea, Send button, queue to DB, auto-mark done
3. **Sender script** -- polls DB, sends via Telethon, marks sent/failed
4. **Cron + deploy** -- 2-min polling, launchd, Vercel deploy

After completion: you can edit AI drafts and send Telegram replies directly from the Kanban dashboard. Messages are sent as YOU (via Telethon), not the bot. Delivery within 2 minutes.
