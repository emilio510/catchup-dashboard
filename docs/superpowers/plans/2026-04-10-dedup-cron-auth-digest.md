# Dedup + Cron + Auth + Digest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deduplication to prevent duplicate triage items, automate scanning every 8h with a local cron that sends a Telegram digest to a dedicated bot chat, and add password authentication to the dashboard.

**Architecture:** Dedup uses chat_id matching against the latest scan's items -- if a chat was already triaged and marked "done" with no new messages, skip it. Cron uses macOS launchd (persists across reboots, runs even when terminal is closed). Digest sends to a configurable Telegram chat ID instead of Saved Messages. Auth uses a simple shared password checked via middleware cookie.

**Tech Stack:** Python asyncpg (dedup queries), macOS launchd (cron), Next.js middleware (auth), Telethon (digest to bot chat)

---

## File Structure

```
scanner/
  src/
    database.py          # MODIFY: add dedup queries (get_previous_items, upsert logic)
    digest.py            # MODIFY: send to configurable chat_id
    scanner.py           # MODIFY: wire dedup before classification
    config.py            # MODIFY: add dashboard_url and digest_chat_id to config
    telegram_reader.py   # MODIFY: add send_message(chat_id, text) method
  tests/
    test_database.py     # MODIFY: add dedup tests
    test_dedup.py        # CREATE: dedup logic tests
  config.yaml            # MODIFY: add digest_chat_id, dashboard_url

scanner/cron/
  catchup-scanner.plist  # CREATE: launchd plist for 8h cron
  run-scan.sh            # CREATE: shell script wrapper

dashboard/
  middleware.ts          # CREATE: password auth middleware
  app/login/page.tsx     # CREATE: login page
  app/login/action.ts    # CREATE: login server action
```

---

### Task 1: Deduplication

**Files:**
- Modify: `scanner/src/database.py`
- Modify: `scanner/src/scanner.py`
- Create: `scanner/tests/test_dedup.py`

The dedup strategy from the spec:
- If a chat has **new messages since last scan** -> create fresh triage item with updated classification
- If a chat has **no new messages** and user marked it "done" -> do NOT resurface
- If a chat has **no new messages** and user has NOT acted -> update `scanned_at` timestamp, keep same priority/content

- [ ] **Step 1: Write failing tests for dedup logic**

```python
# scanner/tests/test_dedup.py
from datetime import datetime, timezone
from src.database import should_reclassify, build_update_scanned_at


def test_should_reclassify_new_messages():
    """Chat has new messages since last scan -> reclassify."""
    last_scan_at = datetime(2026, 4, 10, 10, 0, tzinfo=timezone.utc)
    last_message_at = datetime(2026, 4, 10, 14, 0, tzinfo=timezone.utc)  # after scan
    assert should_reclassify(last_message_at, last_scan_at, "open") is True


def test_should_not_reclassify_done_no_new_messages():
    """Chat marked done, no new messages -> skip entirely."""
    last_scan_at = datetime(2026, 4, 10, 10, 0, tzinfo=timezone.utc)
    last_message_at = datetime(2026, 4, 10, 8, 0, tzinfo=timezone.utc)  # before scan
    assert should_reclassify(last_message_at, last_scan_at, "done") is False


def test_should_not_reclassify_open_no_new_messages():
    """Chat still open, no new messages -> don't reclassify (just update timestamp)."""
    last_scan_at = datetime(2026, 4, 10, 10, 0, tzinfo=timezone.utc)
    last_message_at = datetime(2026, 4, 10, 8, 0, tzinfo=timezone.utc)  # before scan
    assert should_reclassify(last_message_at, last_scan_at, "open") is False


def test_should_reclassify_no_previous_item():
    """No previous triage item for this chat -> classify."""
    assert should_reclassify(datetime.now(timezone.utc), None, None) is True


def test_build_update_scanned_at():
    """Update query should set scanned_at and new scan_id."""
    query, params = build_update_scanned_at("item-uuid", "scan-uuid")
    assert "UPDATE triage_items" in query
    assert "scanned_at" in query
    assert params[0] == "scan-uuid"
    assert params[1] == "item-uuid"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd scanner && .venv/bin/python -m pytest tests/test_dedup.py -v`

- [ ] **Step 3: Add dedup functions to database.py**

Add these functions to `scanner/src/database.py`:

```python
def should_reclassify(
    last_message_at: datetime,
    previous_scan_at: datetime | None,
    previous_user_status: str | None,
) -> bool:
    """Decide whether to reclassify a chat or skip it."""
    if previous_scan_at is None:
        return True  # never scanned before
    if previous_user_status == "done":
        return last_message_at > previous_scan_at  # only if new messages
    # open or snoozed: reclassify only if new messages
    return last_message_at > previous_scan_at


def build_update_scanned_at(item_id: str, new_scan_id: str) -> tuple[str, list]:
    """Update an existing item's scan_id and scanned_at without reclassifying."""
    query = """
        UPDATE triage_items
        SET scan_id = $1::uuid, scanned_at = now()
        WHERE id = $2::uuid
    """
    return query, [new_scan_id, item_id]


async def get_previous_items(database_url: str, chat_ids: list[int]) -> dict[int, dict]:
    """Fetch the most recent triage item per chat_id from the database."""
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd scanner && .venv/bin/python -m pytest tests/test_dedup.py -v`

- [ ] **Step 5: Wire dedup into scanner.py**

In `scanner/src/scanner.py`, modify the `run()` method. After step 2 (read and filter dialogs) and before step 4 (classify), add dedup logic:

```python
            # 3. Dedup: check which conversations need reclassification
            if self._config.output.database_url:
                from src.database import get_previous_items, should_reclassify
                chat_ids = [c.dialog.chat_id for c in conversations]
                previous = await get_previous_items(
                    self._config.output.database_url, chat_ids
                )

                to_classify = []
                skipped_items = []  # items to carry forward without reclassifying
                for conv in conversations:
                    prev = previous.get(conv.dialog.chat_id)
                    if prev is None:
                        to_classify.append(conv)
                    else:
                        last_msg = conv.messages[-1].date if conv.messages else None
                        if should_reclassify(last_msg, prev["scanned_at"], prev["user_status"]):
                            to_classify.append(conv)
                        else:
                            skipped_items.append(prev["id"])

                logger.info(
                    "Dedup: %d to classify, %d unchanged (skipped)",
                    len(to_classify), len(skipped_items),
                )
                conversations = to_classify
            
            if not conversations:
                logger.info("No conversations need reclassification")
                # Still create a scan record and update timestamps of skipped items
                stats = ScanStats(total=0, by_priority=PriorityStats(), by_status={})
                result = ScanResult(
                    sources=["telegram"],
                    dialogs_listed=total_dialogs,
                    dialogs_filtered=filtered_count,
                    dialogs_classified=0,
                    items=[],
                    stats=stats,
                )
                return result
```

Move the existing `my_name` and classification code so it only runs on `conversations` (which now only contains chats needing reclassification).

- [ ] **Step 6: Run full test suite**

Run: `cd scanner && .venv/bin/python -m pytest tests/ -v`
Expected: all tests pass (32+)

- [ ] **Step 7: Commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add scanner/src/database.py scanner/src/scanner.py scanner/tests/test_dedup.py
git commit -m "feat: dedup -- skip reclassification for unchanged and done chats"
```

---

### Task 2: Telegram Digest to Bot Chat

**Files:**
- Modify: `scanner/src/config.py` (add `digest_chat_id`, `dashboard_url`)
- Modify: `scanner/src/telegram_reader.py` (add `send_message` method)
- Modify: `scanner/src/scanner.py` (use chat_id for digest, include dashboard URL)
- Modify: `scanner/config.yaml`

Currently the digest goes to Saved Messages ("me"). We want it to go to a specific chat (the bot chat between you and the bot).

- [ ] **Step 1: Add config fields**

In `scanner/src/config.py`, add to `OutputConfig`:

```python
class OutputConfig(BaseModel):
    telegram_digest: bool = True
    json_file: str = "scan_results.json"
    database_url: str | None = None
    dashboard_url: str | None = None
    digest_chat_id: int | None = None  # Telegram chat ID for digest (None = Saved Messages)
```

In the `from_yaml` method, no env overlay needed -- these go directly in config.yaml.

- [ ] **Step 2: Add generic send_message to TelegramReader**

In `scanner/src/telegram_reader.py`, add:

```python
    async def send_message(self, chat_id: int | str, text: str) -> None:
        assert self._client is not None
        await self._client.send_message(chat_id, text)
```

- [ ] **Step 3: Update scanner.py digest step**

Replace the current digest step in `scanner/src/scanner.py`:

```python
            # 9. Send Telegram digest
            if self._config.output.telegram_digest:
                text = format_digest(result, self._config.output.dashboard_url)
                chat_id = self._config.output.digest_chat_id or "me"
                await self._reader.send_message(chat_id, text)
                logger.info("Digest sent to chat %s", chat_id)
```

- [ ] **Step 4: Update config.yaml**

```yaml
output:
  telegram_digest: true
  json_file: scan_results.json
  dashboard_url: https://catchup-dashboard-akgemilio.vercel.app
  # digest_chat_id: 123456789  # Set to your bot chat ID (get via .chats command or @userinfobot)
```

- [ ] **Step 5: Run tests**

Run: `cd scanner && .venv/bin/python -m pytest tests/ -v`

- [ ] **Step 6: Commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add scanner/src/config.py scanner/src/telegram_reader.py scanner/src/scanner.py scanner/config.yaml
git commit -m "feat: digest to configurable Telegram chat with dashboard URL"
```

---

### Task 3: Dashboard Password Auth

**Files:**
- Create: `dashboard/middleware.ts`
- Create: `dashboard/app/login/page.tsx`
- Create: `dashboard/app/login/action.ts`

Simple cookie-based password auth. One shared password in an env var `DASHBOARD_PASSWORD`. No user accounts needed -- this is a personal tool.

- [ ] **Step 1: Create middleware**

```typescript
// dashboard/middleware.ts
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const isLoginPage = request.nextUrl.pathname === "/login";
  const authCookie = request.cookies.get("catchup-auth");

  if (isLoginPage) {
    return NextResponse.next();
  }

  if (!authCookie || authCookie.value !== "authenticated") {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
```

- [ ] **Step 2: Create login server action**

```typescript
// dashboard/app/login/action.ts
"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export async function loginAction(formData: FormData): Promise<{ error?: string }> {
  const password = formData.get("password") as string;
  const expected = process.env.DASHBOARD_PASSWORD;

  if (!expected) {
    return { error: "DASHBOARD_PASSWORD not configured" };
  }

  if (password !== expected) {
    return { error: "Wrong password" };
  }

  const cookieStore = await cookies();
  cookieStore.set("catchup-auth", "authenticated", {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 60 * 60 * 24 * 30, // 30 days
    path: "/",
  });

  redirect("/");
}
```

- [ ] **Step 3: Create login page**

```typescript
// dashboard/app/login/page.tsx
"use client";

import { useActionState } from "react";
import { loginAction } from "./action";

export default function LoginPage() {
  const [state, formAction, isPending] = useActionState(
    async (_prev: { error?: string }, formData: FormData) => {
      return await loginAction(formData);
    },
    {}
  );

  return (
    <main className="min-h-screen flex items-center justify-center bg-[#0d1117]">
      <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-8 w-80">
        <h1 className="text-lg font-bold text-[#e6edf3] mb-6 text-center">
          Catch-up Dashboard
        </h1>
        <form action={formAction}>
          <input
            type="password"
            name="password"
            placeholder="Password"
            autoFocus
            className="w-full bg-[#0d1117] border border-[#30363d] rounded px-3 py-2 text-sm text-[#e6edf3] placeholder-[#8b949e] outline-none focus:border-[#388bfd] mb-4"
          />
          <button
            type="submit"
            disabled={isPending}
            className="w-full bg-[#238636] hover:bg-[#2ea043] text-white text-sm font-medium py-2 rounded disabled:opacity-50"
          >
            {isPending ? "..." : "Sign in"}
          </button>
          {state.error && (
            <p className="text-[#f85149] text-xs mt-3 text-center">{state.error}</p>
          )}
        </form>
      </div>
    </main>
  );
}
```

- [ ] **Step 4: Set environment variable**

Locally:
```bash
echo "DASHBOARD_PASSWORD=your-secret-password" >> dashboard/.env.local
```

On Vercel:
```bash
cd dashboard && vercel env add DASHBOARD_PASSWORD production
```

- [ ] **Step 5: Verify build**

```bash
cd dashboard && npx tsc --noEmit --skipLibCheck
```

- [ ] **Step 6: Commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/middleware.ts dashboard/app/login/
git commit -m "feat: password auth with cookie-based sessions"
```

---

### Task 4: Cron Scheduling (macOS launchd)

**Files:**
- Create: `scanner/cron/run-scan.sh`
- Create: `scanner/cron/catchup-scanner.plist`

Using macOS launchd because it persists across reboots and runs even when terminal is closed. Runs every 8 hours (3x/day).

- [ ] **Step 1: Create the scan wrapper script**

```bash
#!/bin/bash
# scanner/cron/run-scan.sh
# Wrapper script for launchd cron

SCANNER_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_FILE="$SCANNER_DIR/cron/scan.log"

echo "=== Scan started at $(date -u '+%Y-%m-%d %H:%M UTC') ===" >> "$LOG_FILE"

cd "$SCANNER_DIR" || exit 1
"$SCANNER_DIR/.venv/bin/python" -m src.cli --config config.yaml 2>&1 >> "$LOG_FILE"

echo "=== Scan finished at $(date -u '+%Y-%m-%d %H:%M UTC') ===" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
```

Make it executable:
```bash
chmod +x scanner/cron/run-scan.sh
```

- [ ] **Step 2: Create launchd plist**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.akgemilio.catchup-scanner</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/akgemilio/Projects/catchup-dashboard/scanner/cron/run-scan.sh</string>
    </array>
    <key>StartInterval</key>
    <integer>28800</integer>
    <key>StandardOutPath</key>
    <string>/Users/akgemilio/Projects/catchup-dashboard/scanner/cron/launchd-stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/akgemilio/Projects/catchup-dashboard/scanner/cron/launchd-stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
    </dict>
</dict>
</plist>
```

Note: `StartInterval` 28800 = 8 hours in seconds.

- [ ] **Step 3: Install the launchd job**

```bash
cp scanner/cron/catchup-scanner.plist ~/Library/LaunchAgents/com.akgemilio.catchup-scanner.plist
launchctl load ~/Library/LaunchAgents/com.akgemilio.catchup-scanner.plist
```

Verify it's loaded:
```bash
launchctl list | grep catchup
```

- [ ] **Step 4: Test a manual trigger**

```bash
launchctl start com.akgemilio.catchup-scanner
# Wait ~4 minutes, then check
tail -20 scanner/cron/scan.log
```

Expected: scan runs, classifies, pushes to DB, sends digest.

- [ ] **Step 5: Add cron files to gitignore**

Add to `.gitignore`:
```
scanner/cron/*.log
```

- [ ] **Step 6: Commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add scanner/cron/run-scan.sh scanner/cron/catchup-scanner.plist .gitignore
git commit -m "feat: launchd cron job -- auto-scan every 8h with digest"
```

---

### Task 5: Deploy + Push

- [ ] **Step 1: Set DASHBOARD_PASSWORD on Vercel**

```bash
cd dashboard && vercel env add DASHBOARD_PASSWORD production
```

Enter your chosen password when prompted.

- [ ] **Step 2: Deploy**

```bash
vercel --prod
```

- [ ] **Step 3: Push to GitHub**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git push
```

- [ ] **Step 4: Get digest chat ID**

To find the chat ID of your conversation with the bot, you can run:

```bash
cd scanner && .venv/bin/python3 -c "
import asyncio
from src.config import ScannerConfig
from src.telegram_reader import TelegramReader
from pathlib import Path

async def main():
    config = ScannerConfig.from_yaml(Path('config.yaml'))
    reader = TelegramReader(config)
    await reader.connect()
    async for d in reader._client.iter_dialogs(limit=20):
        if d.entity and hasattr(d.entity, 'bot') and d.entity.bot:
            print(f'{d.id}: {d.name}')
    await reader.disconnect()

asyncio.run(main())
" 2>&1 | grep -v DEBUG | grep -v telethon
```

Update `config.yaml` with the bot chat ID.

- [ ] **Step 5: Test full flow**

Run the scanner manually once with digest enabled:
```bash
cd scanner && .venv/bin/python -m src.cli --config config.yaml
```

Verify: dashboard shows data, Telegram bot chat receives digest with dashboard link.

---

## Summary

5 tasks:
1. **Dedup** -- skip reclassification for unchanged/done chats
2. **Digest to bot chat** -- configurable chat_id + dashboard URL in digest
3. **Dashboard auth** -- simple password middleware
4. **Cron** -- launchd every 8h
5. **Deploy + wire up** -- env vars, bot chat ID, test full flow

After completion: scanner runs automatically 3x/day, sends digest to your Telegram bot chat with a link to the dashboard, skips items you've already handled.
