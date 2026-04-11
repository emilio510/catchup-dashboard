# Catchup Dashboard Phase 2: Bot Trigger, Escalation, Auto-Refresh, Analytics, Smarter Dedup

## Overview

Five features that make the system more self-aware and less manual. All stay within the existing hybrid architecture (Python on VPS, Next.js on Vercel, Neon Postgres in between). No new infrastructure.

**Implementation workflow:** Each feature follows implement -> code review -> fix findings -> re-review -> deploy only when clean.

---

## Feature 1: Bot Trigger (On-Demand Scan)

### Summary

Send `/scan` to @akgbaambot on Telegram to trigger an immediate scan, instead of waiting for the next cron run.

### Architecture

- New Python module `bot_listener.py` -- a long-running process on the VPS.
- Calls Telegram Bot API `getUpdates` every 30 seconds with a stored `offset` to avoid reprocessing old messages.
- Recognizes `/scan` command from user ID 1744950707 only. Ignores all other messages and users.
- On `/scan`: replies "Starting scan..." via Bot API, spawns the scanner as a subprocess (`python -m src.cli`), then replies with the result summary or error.
- Runs as a **systemd service** on VPS (not cron), since it needs to be always-on.
- Persists the `offset` to a small file (`~/.catchup-bot-offset`) so restarts don't replay old messages.

### Guard Rails

- **Auth:** Only user ID 1744950707 can trigger scans.
- **Debounce:** If a scan is already running (tracked via subprocess handle), reply "Scan already in progress" instead of spawning another.
- **Offset persistence:** File-based, survives restarts.

### Files

- New: `scanner/src/bot_listener.py`
- New: `scanner/systemd/catchup-bot.service` (systemd unit file)
- Modified: none

---

## Feature 2: Notification Escalation

### Summary

If a P0/P1 item sits unanswered past a configurable threshold, the bot sends a reminder.

### Architecture

- New Python module `escalation.py` on the VPS.
- Runs on its own cron schedule (`0 * * * *`, every hour on the hour).
- Queries Neon for open triage items where `user_status = 'open'` and `waiting_since` exceeds the priority's threshold.
- Sends a reminder via @akgbaambot with item details (chat name, waiting person, how long overdue).

### Configuration

In `config.yaml`:
```yaml
escalation:
  P0: 24   # hours before reminder
  P1: 48
  P2: null # no reminder
  P3: null
```

### Schema Change

Add column to `triage_items`:
```sql
ALTER TABLE triage_items ADD COLUMN last_reminded_at TIMESTAMPTZ;
```

### Guard Rails

- **No spam:** `last_reminded_at` prevents duplicate reminders within the same window. Only re-reminds if the full threshold has passed since the last reminder.
- **Priority changes:** If a scan reclassifies P0 -> P2, the new (null) threshold applies -- no more reminders.
- **Done/snoozed:** Never reminded.

### Files

- New: `scanner/src/escalation.py`
- New: `scanner/cron/escalation-crontab.txt`
- Modified: `schema.sql` (add `last_reminded_at`)
- Modified: `config.yaml` (add escalation section)

---

## Feature 3: Dashboard Auto-Refresh

### Summary

Dashboard polls for new data every 30 minutes so you don't have to manually reload. Shows last-refreshed time and a manual refresh button.

### Architecture

- New client component `auto-refresh.tsx` that wraps the page content.
- Uses `setInterval` with `router.refresh()` every 30 minutes. This re-fetches server component data without a full page reload.
- **Visibility-aware:** Skips polling ticks when the tab is backgrounded (`document.hidden`). Refreshes immediately when the tab becomes visible if the interval has elapsed.
- Status element: "Last refreshed: X min ago" (updates every minute) + manual refresh button.
- Placement: in the stats bar area, right-aligned.

### Files

- New: `dashboard/components/auto-refresh.tsx`
- Modified: `dashboard/app/page.tsx` (wrap content with auto-refresh)
- Modified: `dashboard/components/stats-bar.tsx` (add refresh indicator)

---

## Feature 4: Analytics (Inbox Health Over Time)

### Summary

Line chart showing open P0/P1/P2/P3 counts over time, so you can see whether your backlog is growing or shrinking.

### Architecture

- New dashboard page at `/analytics`.
- Data source: existing `scans` + `triage_items` tables. Query-time aggregation, no new tables.
- Query: group `triage_items` by `scan_id` and `priority`, count where `user_status = 'open'`, join with `scans.scanned_at` for x-axis.
- Chart library: **Chart.js** via `react-chartjs-2`.
- 4 colored lines matching Kanban colors: P0 red (#f85149), P1 amber (#d29922), P2 green (#3fb950), P3 gray (#8b949e).
- Time range selector: 7d / 30d / 90d buttons.
- Navigation link between main dashboard and analytics page.

### UI

- X-axis: scan timestamps
- Y-axis: count of open items
- Hover tooltip: exact counts per priority at each scan point

### Files

- New: `dashboard/app/analytics/page.tsx`
- New: `dashboard/components/analytics-chart.tsx`
- Modified: `dashboard/lib/db.ts` (add analytics query)
- Modified: `dashboard/components/stats-bar.tsx` or layout (add nav link)

---

## Feature 5: Smarter Dedup

### Summary

Pass previous classification context to the AI classifier so it makes more informed decisions. Prevents priority flip-flops and false resurrection of done items.

### Architecture

- When `should_reclassify()` returns true and previous data exists, pass it to the classifier prompt.
- Previous context per chat includes: priority, status, user_status, and preview (summary).
- Two new instructions in the classification system prompt:
  1. **Priority stability:** "If the previous priority was assigned by a prior scan, do not downgrade it unless the new messages clearly resolve the conversation. When in doubt, keep the previous priority."
  2. **Done item awareness:** "If the user marked this item as done, only re-triage as open if the new messages genuinely reopen the conversation (new question, new request, new topic). Reactions, 'thanks', acknowledgments, and other low-signal messages should not reopen a done item."

### Data Flow

- `get_previous_items()` already fetches the previous triage item per `chat_id`. Currently used only for the skip/reclassify decision.
- Extend it to also return `priority`, `status`, `user_status`, `preview` for chats being reclassified.
- `classify_batch()` gets an optional `previous_context: dict[str, PreviousItem]` parameter keyed by chat name.
- The classifier can still override -- it has full context. But it's nudged toward stability.

### Schema Changes

None. All data already exists in `triage_items`.

### Files

- Modified: `scanner/src/scanner.py` (pass previous context to classifier)
- Modified: `scanner/src/classifier.py` (accept previous context, update prompt)
- Modified: `scanner/src/database.py` (extend `get_previous_items` return)

---

## Implementation Order

1. **Smarter dedup** -- no new infra, improves existing behavior, good warmup
2. **Notification escalation** -- small schema change + new module, independent
3. **Bot trigger** -- new systemd service, independent from dashboard
4. **Dashboard auto-refresh** -- frontend only, independent
5. **Analytics** -- new page + chart dependency, builds on existing data

Each feature is independently deployable. The order prioritizes foundational improvements (dedup, escalation) before UX additions (auto-refresh, analytics).

---

## Dependencies

- **Chart.js + react-chartjs-2**: new npm dependency for analytics
- **No other new dependencies** for scanner (uses existing stdlib + Telegram Bot API via requests)

## Testing Strategy

- Scanner features: pytest unit tests (extend existing 43-test suite)
- Dashboard features: manual verification on Vercel preview deployments
- Each feature gets code review before deploy
