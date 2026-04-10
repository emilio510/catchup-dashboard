# Catch-up Dashboard -- Design Spec

**Date:** 2026-04-10
**Author:** akgemilio + Claude
**Status:** Draft

## Problem

akgemilio reads all Telegram messages promptly (clears notifications multiple times daily) but frequently doesn't reply. This means conversations where collaborators are waiting on a response look "clean" (no unread indicator) despite needing action. Combined with 50-100 active Telegram chats, Notion pings, and GitHub tasks, important items fall through the cracks.

## Solution

A personal priority tracker that scans communication channels, detects conversations where someone is waiting on a response, classifies them by urgency, and presents them in a Kanban-style dashboard.

## Architecture

### Hybrid: Local Scanner + Deployed Dashboard

```
LOCAL (machine or VPS)
  Python scanner (Telethon + Notion API + GitHub API + Google Calendar)
  Runs on cron or on-demand
  Pushes scan results to database

VERCEL
  Next.js dashboard (reads from database)
  Kanban view, filters, search, mark as done
  Accessible from phone/desktop
```

**Why hybrid:** Telethon requires a persistent MTProto session file and Python runtime. It cannot run in Vercel Functions. The scanner runs locally where the session file lives; the dashboard deploys to Vercel for access from anywhere.

### Build Order

1. **Scanner** (Python + Telethon) -- core logic, runs locally
2. **Database** (Neon Postgres via Vercel Marketplace)
3. **Dashboard** (Next.js on Vercel, Kanban layout)
4. **Cron** (local crontab triggers scanner every 2h)
5. **Telegram digest** (scanner sends summary to Saved Messages after each run)

## Scanner Design

### Pipeline

```
1. List All Dialogs (iter_dialogs, ~50-100 chats)
       |
2. Fast Filter
   - Remove blacklisted chats (from config YAML)
   - Remove broadcast channels
   - Remove bot chats (unless whitelisted)
   - Remove chats where YOU sent the last message
       |
3. Deep Read (~25-50 remaining)
   - Fetch last 20 messages per chat
   - Include sender identity, timestamps, reply chains
       |
4. AI Classification (Claude API, batches of ~5 chats)
   - Priority: P0 / P1 / P2 / P3
   - Status: NEW / READ_NO_REPLY / REPLIED / MONITORING
   - Who is waiting on you (specific person name)
   - How long they've been waiting (first unanswered message timestamp)
   - Tags (AI-generated: "meeting request", "deliverable", "follow-up", etc.)
   - Draft reply suggestion
   - Rule: when in doubt between two priorities, always choose the higher one
       |
5. Output
   - Push to Postgres (for dashboard)
   - Generate Telegram digest (send to Saved Messages)
```

### Fast Filter Logic

A chat is **removed** from the scan if ANY of these are true:
- Chat ID or name is in the blacklist config
- Chat is a broadcast channel (no reply possible)
- Chat is a bot (unless explicitly whitelisted)
- The last message in the chat was sent by you (ball is in their court)

Everything else proceeds to deep read. No time-based conditions on the filter.

### Scan Window

- **Default: 7 days** -- fetches messages from the last 7 days
- Configurable per run for deep catch-up sessions

### AI Classification Prompt Strategy

Each batch of ~5 chats is sent to Claude with:
- Your Telegram user ID and display name (so it knows which messages are yours)
- The last 20 messages per chat with sender names and timestamps
- Instructions to classify priority, detect who's waiting, estimate wait duration
- The "when in doubt, go higher" rule
- Context about your role (TokenLogic, Aave governance, Logic Protocol) to help prioritize

### Config File (YAML)

```yaml
# config.yaml
scan:
  window_days: 7
  messages_per_chat: 20
  batch_size: 5

telegram:
  session_name: akgemilio
  blacklist:
    - "Monitoring Alerts"
    - "DeFi News Channel"
    - "Bot: PriceTracker"
  # bot_whitelist: []  # bots to include in scan

classification:
  model: claude-sonnet-4-20250514
  user_context: |
    I work at TokenLogic (Aave treasury/service provider).
    Building Logic Protocol (cross-chain yield product).
    Key collaborators: StraitsX, Mantle, Aave governance participants.
    I manage incentive programs, vault development, and governance proposals.

output:
  telegram_digest: true  # send summary to Saved Messages
  database_url: ${DATABASE_URL}  # Neon Postgres
```

## Data Model

### Postgres Schema

```sql
CREATE TABLE scans (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scanned_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  sources       TEXT[] NOT NULL,          -- ['telegram', 'notion', 'github']
  dialogs_listed     INT NOT NULL,
  dialogs_filtered   INT NOT NULL,
  dialogs_classified INT NOT NULL,
  stats         JSONB NOT NULL            -- { total, by_priority, by_status }
);

CREATE TABLE triage_items (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scan_id         UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
  source          TEXT NOT NULL,           -- 'telegram' | 'notion' | 'github' | 'calendar'

  -- Who & where
  chat_name       TEXT NOT NULL,
  chat_type       TEXT NOT NULL,           -- 'dm' | 'group'
  waiting_person  TEXT,                    -- who specifically needs you

  -- Content
  preview         TEXT NOT NULL,           -- last relevant message, truncated
  context_summary TEXT,                    -- AI summary of thread context
  draft_reply     TEXT,                    -- AI-suggested response

  -- Classification
  priority        TEXT NOT NULL,           -- 'P0' | 'P1' | 'P2' | 'P3'
  status          TEXT NOT NULL DEFAULT 'READ_NO_REPLY',
  tags            TEXT[] DEFAULT '{}',

  -- Timing
  last_message_at  TIMESTAMPTZ,
  waiting_since    TIMESTAMPTZ,           -- first unanswered message
  waiting_days     INT,

  -- Metadata
  scanned_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  chat_id          BIGINT,                -- Telegram chat ID
  message_id       BIGINT,                -- for deep linking

  -- User actions (dashboard state)
  user_status      TEXT DEFAULT 'open',   -- 'open' | 'done' | 'snoozed'
  user_status_at   TIMESTAMPTZ
);

CREATE INDEX idx_triage_scan ON triage_items(scan_id);
CREATE INDEX idx_triage_priority ON triage_items(priority);
CREATE INDEX idx_triage_user_status ON triage_items(user_status);
```

### Key distinction: `status` vs `user_status`

- **`status`** is AI-detected from the conversation (READ_NO_REPLY, NEW, MONITORING)
- **`user_status`** is set by the user in the dashboard (open, done, snoozed)

This means you can mark items as "done" in the dashboard and they won't clutter future views, even if the scanner picks them up again on the next run.

## Dashboard Design

### Layout: Kanban Board

Four columns: P0 (Today) | P1 (This Week) | P2 (Respond) | P3 (Monitor)

Each column has:
- Header with priority color dot, label, and item count
- Cards showing: title, waiting person, preview, source badge, wait time badge, tags
- Click card to expand: full context summary, draft reply, action buttons

### Features
- **Filter bar:** source (Telegram/Notion/GitHub/Calendar), chat type (DM/Group), status (open/done/snoozed)
- **Search:** full-text across titles, previews, person names
- **Mark as done:** checkbox or button per item, updates `user_status`
- **Snooze:** push item out of view until next scan
- **Scan metadata:** header shows last scan time, dialogs scanned, total items
- **Mobile responsive:** usable from phone

### Color Scheme
- Dark theme (GitHub-inspired, matching mockup)
- P0: red (#f85149), P1: amber (#d29922), P2: green (#3fb950), P3: gray (#8b949e)
- Source badges: Telegram blue, Notion purple, GitHub white, Calendar green

### Tech Stack
- Next.js App Router
- Tailwind CSS
- Server Components for data fetching
- No client-side state management needed (server reads from Postgres)

## Telegram Digest

After each scan, the scanner sends a summary to Telegram Saved Messages:

```
Catch-up Dashboard -- Apr 10, 14:00

P0 (5 items):
- StraitsX x Grab: Marc waiting 3d on vault parameters
- TokenLogic Core: Matt needs budget sign-off (2nd ping)
- [3 more]

P1 (8 items):
- USDT0 keeper spec: team tagged you on Notion
- Mantle call prep: tomorrow 3pm, unanswered Qs
- [6 more]

34 total items | Dashboard: https://your-app.vercel.app
```

## Sources (V1 vs Later)

### V1
- **Telegram** (Telethon MTProto) -- DMs + group chats, 7-day window, blacklist
- **Notion** (existing MCP or API) -- pages where you're mentioned/tagged
- **GitHub** (API) -- issues/PRs assigned to you or requesting review
- **Google Calendar** (API) -- upcoming events that boost priority of related conversations

### Later
- Slack (when volume increases)
- Discord (needs MCP or bot setup)
- Gmail (if needed)

## Security Considerations

- **Telethon session file** (`akgemilio.session`) is a bearer credential. Never commit to git, never expose.
- **API keys** stored in `.env`, never in config.yaml
- **Database URL** via environment variable
- **Dashboard** should be behind auth (Vercel auth or simple password) since it contains message previews
- **Scanner is read-only** -- never sends messages on your behalf (except digest to Saved Messages)
- **No message content stored long-term** -- `preview` and `context_summary` are truncated/summarized. Full messages stay in Telegram.

## Project Structure

```
catchup-dashboard/
  scanner/                  # Python
    src/
      scanner.py            # Main orchestrator
      telegram_scanner.py   # Telethon dialog scanning
      notion_scanner.py     # Notion mentions
      github_scanner.py     # GitHub assigned issues/PRs
      calendar_scanner.py   # Google Calendar upcoming events
      classifier.py         # Claude API classification
      database.py           # Postgres push
      digest.py             # Telegram digest sender
      config.py             # YAML config loader
    config.yaml
    requirements.txt
    .env

  dashboard/                # Next.js
    app/
      page.tsx              # Kanban board
      api/                  # API routes if needed
    components/
      KanbanBoard.tsx
      KanbanColumn.tsx
      TriageCard.tsx
      FilterBar.tsx
      SearchBar.tsx
    lib/
      db.ts                 # Postgres client
      types.ts              # Shared types
    vercel.json
    .env.local

  docs/
    superpowers/specs/
      2026-04-10-catchup-dashboard-design.md  # this file
```

## Deduplication Strategy

When the scanner runs again and encounters a chat that was already triaged:
- If the chat has **new messages since the last scan** (someone spoke after the previous scan timestamp), create a fresh triage item with updated classification.
- If the chat has **no new messages** and the user marked it "done", do not resurface it.
- If the chat has **no new messages** and the user has NOT acted on it, update the existing item's `scanned_at` timestamp but keep the same priority/content (don't waste a Claude API call re-classifying identical data).

This prevents "done" items from reappearing while still catching new activity in previously-triaged chats.

## Open Questions

None -- design is complete. Ready for implementation planning.
