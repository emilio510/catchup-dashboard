# Catch-up Dashboard

Personal priority tracker that scans your Telegram conversations, classifies them by urgency using AI, and presents them in a Kanban dashboard you can access from anywhere. Automated scans run 3x/day, on-demand via Telegram bot command, with escalation reminders for overdue items.

**Problem:** You read all your messages but don't always reply. No unread indicator means important conversations fall through the cracks across dozens of active chats.

**Solution:** A scanner reads your Telegram chats, detects who's waiting on a response, classifies priority (P0-P3), and pushes results to a live dashboard with filters, search, draft replies, analytics, and auto-refresh.

## How It Works

```
Scanner (Python, runs on VPS cron 3x/day + on-demand via bot)
  Telethon MTProto -> List dialogs -> Filter -> Dedup -> Deep read
  -> Claude API classification (with previous context for stability)
  -> Push to Postgres
  -> Google Calendar -> Standalone event cards (P0-P3 by proximity)
  -> Telegram digest via bot

Bot Listener (Python, systemd service on VPS)
  Polls Telegram getUpdates every 30s
  -> /scan command triggers on-demand scan
  -> Auth-gated to owner only

Escalation (Python, hourly cron on VPS)
  Queries overdue P0 (>24h) and P1 (>48h) items
  -> Sends reminder via Telegram bot
  -> Anti-spam via last_reminded_at tracking

Dashboard (Next.js, deployed on Vercel)
  Reads from Postgres -> Kanban board (P0/P1/P2/P3)
  -> Mark done / Snooze / Search / Filter
  -> Auto-refresh every 30 min + manual refresh button
  -> /analytics page with inbox health trend chart
  -> Password-protected
```

### Priority Levels

- **P0 -- Respond Today:** Someone is actively blocked, deal-critical, or pinged multiple times
- **P1 -- This Week:** Important deliverable, meeting prep, or time-sensitive request
- **P2 -- Respond:** Question or request, not urgent
- **P3 -- Monitor:** FYI, general discussion, no action needed

When in doubt, the classifier always chooses the higher priority.

## Features

- **Smart filtering** -- skips channels, bots, blacklisted chats, and chats where you spoke last
- **Deduplication** -- only reclassifies chats with new messages since last scan; items you marked "done" stay done
- **Kanban dashboard** -- 4 priority columns, expandable cards with context + AI draft reply
- **Telegram digest** -- bot sends you a summary every 8h with a link to the dashboard
- **Password auth** -- dashboard is protected behind a login page
- **Mobile responsive** -- works on phone
- **Reply from dashboard** -- edit AI drafts and send Telegram messages directly from the Kanban board (queued, sent within 2 min as you)
- **Team-aware classification** -- knows your teammates (boss, lead dev) and lowers priority when they already responded
- **@mention detection** -- direct pings to you are boosted to P0/P1
- **Graceful degradation** -- if DB or digest fails, scan results are still saved to JSON
- **On-demand scan** -- send `/scan` to your Telegram bot to trigger an immediate scan from anywhere
- **Escalation reminders** -- overdue P0 (>24h) and P1 (>48h) items trigger automatic Telegram reminders, configurable per priority
- **Smarter dedup** -- classifier receives previous classification context, prevents priority flip-flops and false resurrection of done items
- **Auto-refresh dashboard** -- data refreshes every 30 minutes with visibility awareness (skips when tab is hidden), plus manual refresh button
- **Analytics** -- `/analytics` page with line chart showing open P0/P1/P2/P3 counts over time (7d/30d/90d selector)
- **Notion source** -- scans for comment @mentions (AI-classified) and database assignments (rule-based P2). Configurable databases and monitored pages. Requires a Notion integration with access to the team workspace.

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+ with pnpm
- A Telegram account with API credentials ([my.telegram.org](https://my.telegram.org))
- A Telegram bot for digests (create via [@BotFather](https://t.me/BotFather))
- An Anthropic API key ([console.anthropic.com](https://console.anthropic.com))
- A Neon Postgres database ([neon.tech](https://neon.tech))
- A Vercel account for deployment ([vercel.com](https://vercel.com))
- (Optional) Google Cloud project with Calendar API enabled ([console.cloud.google.com](https://console.cloud.google.com))

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/catchup-dashboard.git
cd catchup-dashboard

# Scanner
cd scanner
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Dashboard
cd ../dashboard
pnpm install
```

### 2. Configure credentials

Create `scanner/.env`:

```env
TELEGRAM_API_ID=your-api-id
TELEGRAM_API_HASH=your-api-hash
ANTHROPIC_API_KEY=your-anthropic-api-key
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require
DIGEST_BOT_TOKEN=your-bot-token-from-botfather
```

Create `dashboard/.env.local`:

```env
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require
DASHBOARD_PASSWORD=your-chosen-password
```

### 3. Set up the database

Run `schema.sql` against your Neon database via the Neon SQL Editor or any Postgres client.

### 4. Configure the scanner

Edit `scanner/config.yaml`:

```yaml
scan:
  window_days: 7          # How far back to scan messages
  messages_per_chat: 20   # Messages to read per chat
  batch_size: 5           # Chats per Claude API call
  max_dialogs: 50         # Top N most active dialogs to scan

telegram:
  session_name: your-username
  blacklist:              # Chats to skip entirely
    - "News Channel"
    - "Monitoring Alerts"
    - "Public Community Group"
  bot_whitelist: []       # Bots to include in scan

classification:
  model: claude-sonnet-4-20250514
  max_tokens: 4096
  rate_limit_rpm: 30
  user_context: |
    Describe your role and key collaborators here.
    This helps the AI classify priorities accurately.

output:
  telegram_digest: true
  json_file: scan_results.json
  dashboard_url: https://your-dashboard.vercel.app
  digest_chat_id: 123456789  # Your Telegram user ID (bot sends TO you)
  # digest_bot_token: set via DIGEST_BOT_TOKEN env var
  # database_url: set via DATABASE_URL env var
```

To find your Telegram user ID, send a message to [@userinfobot](https://t.me/userinfobot).

### 5. First scan

```bash
cd scanner
source .venv/bin/activate

# First run will prompt for phone number + 2FA code
python -m src.cli --config config.yaml --no-digest -v
```

This connects to Telegram, scans your chats, classifies them, and pushes results to the database.

### 6. Launch the dashboard locally

```bash
cd dashboard
pnpm dev
# Open http://localhost:3000
```

### 7. Deploy to Vercel

```bash
cd dashboard
vercel link --yes
printf "your-db-url" | vercel env add DATABASE_URL production
printf "your-password" | vercel env add DASHBOARD_PASSWORD production
vercel --prod
```

Note: use `printf` (not `echo`) to avoid trailing newlines in env var values.

### 8. Set up automated scanning

The scanner needs to run on an always-on machine (VPS recommended) so it works even when your laptop is closed.

**Option A: VPS (recommended)**

Deploy to any Linux VPS (Ubuntu, Debian, etc.):

```bash
# On the VPS:
git clone https://github.com/YOUR_USERNAME/catchup-dashboard.git
cd catchup-dashboard/scanner
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Copy secrets from your local machine:
# scp scanner/.env scanner/akgemilio.session scanner/token.json scanner/credentials.json user@vps:~/catchup-dashboard/scanner/

# Set up crontab (scanner 3x/day + sender every 2 min):
crontab -e
```

Add these lines:
```cron
# Scanner at 7am, 1pm, 9pm UTC
0 7 * * * cd ~/catchup-dashboard/scanner && .venv/bin/python -m src.cli --config config.yaml >> cron/scan.log 2>&1
0 13 * * * cd ~/catchup-dashboard/scanner && .venv/bin/python -m src.cli --config config.yaml >> cron/scan.log 2>&1
0 21 * * * cd ~/catchup-dashboard/scanner && .venv/bin/python -m src.cli --config config.yaml >> cron/scan.log 2>&1

# Sender (polls for queued replies every 2 min)
*/2 * * * * cd ~/catchup-dashboard/scanner && .venv/bin/python -m src.sender --config config.yaml >> cron/sender.log 2>&1

# Escalation reminders (hourly)
0 * * * * cd ~/catchup-dashboard/scanner && .venv/bin/python -m src.escalation --config config.yaml >> cron/escalation.log 2>&1
```

Set up the bot listener as a systemd service:
```bash
sudo cp ~/catchup-dashboard/scanner/systemd/catchup-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now catchup-bot
```

**Option B: macOS (runs only when laptop is open)**

```bash
cp scanner/cron/catchup-scanner.plist ~/Library/LaunchAgents/com.akgemilio.catchup-scanner.plist
# Edit paths in the plist if your username differs
launchctl load ~/Library/LaunchAgents/com.akgemilio.catchup-scanner.plist
```

Note: macOS launchd `StartCalendarInterval` fires missed jobs after waking from sleep, but won't run while the laptop is closed.

### 9. (Optional) Connect Google Calendar

Google Calendar events boost priority of related Telegram chats and give the classifier meeting prep context.

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project and enable **Google Calendar API**
3. Go to APIs & Services > Credentials > Create **OAuth 2.0 Client ID** (Desktop App)
4. Download the JSON and save as `scanner/credentials.json`
5. Run the auth flow (opens browser):
```bash
cd scanner && .venv/bin/python3 -c "
from src.calendar_scanner import _get_credentials
from pathlib import Path
_get_credentials(Path('credentials.json'), Path('token.json'))
print('Auth successful!')
"
```
6. Enable in `scanner/config.yaml`:
```yaml
calendar:
  enabled: true
```

The scanner will now fetch your next 7 days of events and use them to boost related chat priority.

## Usage

### Daily workflow

The scanner runs automatically 3x/day (7am, 1pm, 9pm UTC) and sends a Telegram digest. If a P0 item sits unanswered for 24h, you get a reminder. When you want to catch up:

1. Check the digest in Telegram (from your bot)
2. Open the dashboard for the full Kanban view
3. Check `/analytics` to see if your inbox is growing or shrinking
4. Expand cards to see context + draft replies
5. Edit the AI draft reply if needed, click **Send reply** -- message is sent as you within 2 min
6. Or mark items as done / snooze them

### On-demand scan

Send `/scan` to your bot on Telegram. The bot replies "Starting scan..." and notifies you when done. No need to SSH into the VPS.

### Manual scan (CLI)

```bash
cd scanner && python -m src.cli --config config.yaml
```

### CLI options

```
--config PATH       Path to config.yaml (default: config.yaml)
--window-days N     Override scan window in days
--max-dialogs N     Limit number of dialogs to scan
--no-digest         Skip sending Telegram digest
--output PATH       Override output JSON path
-v, --verbose       Enable debug logging
```

### Dashboard features

- **Kanban board** with P0/P1/P2/P3 columns
- **Expandable cards** with context summary, editable AI-drafted reply, and **Send** button
- **Filters** by source, chat type (DM/group), status (open/done/snoozed)
- **Search** across chat names, people, and message previews
- **Mark as done / Snooze** to clear handled items
- **Auto-refresh** every 30 minutes (visibility-aware, with manual refresh button)
- **Analytics** at `/analytics` -- line chart of open item counts per priority over time
- **Mobile responsive** -- usable from phone
- **Password protected** -- cookie-based auth with 30-day sessions

## Architecture

```
catchup-dashboard/
  scanner/                # Python -- runs on VPS
    src/
      cli.py              # CLI entry point
      scanner.py          # Orchestrator (read -> dedup -> classify -> push -> digest)
      sender.py           # Reply sender (polls pending_replies, sends via Telethon)
      bot_listener.py     # Telegram bot listener (getUpdates polling, /scan command)
      escalation.py       # Overdue item reminders (P0 >24h, P1 >48h)
      notion_scanner.py   # Notion API: comment @mentions + database assignments
      calendar_scanner.py # Google Calendar: fetch events, find related chats
      telegram_reader.py  # Telethon: list dialogs, filter, deep read
      classifier.py       # Claude API batch classification (with previous context)
      database.py         # Postgres push + dedup queries (asyncpg)
      digest.py           # Telegram digest formatter
      config.py           # YAML + env config loader (scan, telegram, classification, escalation)
      models.py           # Pydantic data models
    tests/                # 78 tests
    config.yaml           # Scanner configuration + team context + escalation thresholds
    cron/                 # crontab entries (scanner 3x/day, sender 2min, escalation hourly)
    systemd/              # catchup-bot.service (bot listener)
    migrations/           # SQL migration files

  dashboard/              # Next.js 16 -- deployed on Vercel
    app/
      page.tsx            # Main Kanban page (Server Component)
      analytics/page.tsx  # Inbox health trend chart
      actions.ts          # Server Actions (done/snooze/reopen/sendReply)
      api/login/route.ts  # Login API endpoint
      login/page.tsx      # Login page
    components/
      kanban-board.tsx    # Kanban grid layout
      triage-card.tsx     # Expandable item card with draft reply
      stats-bar.tsx       # Header with stats, auto-refresh, analytics link
      auto-refresh.tsx    # Client component: 30-min polling + visibility awareness
      analytics-chart.tsx # Chart.js line chart (P0-P3 over time)
      filter-bar.tsx      # Source, type, status filters
    lib/
      db.ts               # Neon Postgres queries (triage items + analytics)
      types.ts            # Shared TypeScript types
    middleware.ts          # Auth middleware

  schema.sql              # Postgres schema (scans + triage_items + pending_replies)
```

### Smart filtering pipeline

```
874 total dialogs
  -> Remove blacklisted (43 entries)
  -> Remove broadcast channels
  -> Remove bot chats
  -> Remove chats where you spoke last
  -> Take top 50 most recently active
  -> Dedup: skip unchanged chats from previous scan
  -> ~5-15 chats actually classified per run
  + Google Calendar: 7-day lookahead -> standalone event cards
    (P0=today, P1=2d, P2=3-5d, P3=6d+)
```

### Key design decisions

- **No unread-based filtering:** The scanner detects who's waiting by analyzing message content, not read status. This works even if you read everything and clear notifications.
- **Deduplication:** Only chats with new messages since the last scan are reclassified. Items you marked "done" stay done unless new messages arrive. The dedup comparison uses the dialog's latest message timestamp (from Telegram's dialog listing), not the deep-read message list which is capped by `messages_per_chat`.
- **Cross-scan queries:** The dashboard shows the most recent item per chat across all scans, not just the latest scan. This means items from previous scans persist correctly.
- **Batch classification:** Chats are sent to Claude in batches of 5 for cost efficiency (~$0.02-0.05 per scan).
- **Retry with backoff:** API overload errors are retried (3 attempts, exponential backoff, inter-batch delay).
- **Graceful degradation:** If DB push or digest fails, scan results are still saved to JSON and the scan continues.
- **Bot API for digest:** Digest is sent via the Telegram Bot API (not your user account), so messages come from the bot.
- **Queue-based replies:** Dashboard queues replies in Postgres; a sender script (2-min cron) sends them via Telethon as your user account. Row locking prevents duplicate sends.
- **Team-aware classification:** Knows your boss (Matthew Graham) and lead dev (efecarranza). If they already responded, priority is lowered automatically.
- **@mention boosting:** Messages that @mention you or address you by name are boosted to P0/P1.
- **Calendar cards:** Google Calendar events appear as standalone triage items with auto-priority based on proximity (today=P0, tomorrow=P1, etc.). They also inject context into the classifier so related Telegram chats get boosted.
- **Priority stability:** When reclassifying a chat, the classifier receives the previous priority, status, and summary. It won't downgrade unless new messages clearly resolve the conversation.
- **Done item awareness:** If you marked something done and a "thanks" or reaction arrives, the classifier keeps it at P3/MONITORING instead of reopening it.
- **Escalation anti-spam:** Reminders track `last_reminded_at` per item and only re-remind after a full threshold window (24h for P0, 48h for P1). Uses `FOR UPDATE SKIP LOCKED` to prevent duplicate reminders from concurrent cron runs.
- **Bot token security:** httpx request logging is suppressed to prevent bot tokens from appearing in systemd journal logs.

## Roadmap

- [x] Telegram scanner with smart filtering
- [x] AI classification (P0-P3) with Claude
- [x] Next.js Kanban dashboard on Vercel
- [x] Deduplication across scans
- [x] Telegram digest via bot
- [x] VPS deployment (always-on, survives laptop sleep)
- [x] Password authentication
- [x] Reply from dashboard (edit AI drafts + send via Telegram)
- [x] Team-aware classification (boss + lead dev responses)
- [x] @mention detection and priority boosting
- [x] Google Calendar integration (standalone event cards + boosts related chat priority)
- [x] Smarter dedup (previous classification context, priority stability, done item awareness)
- [x] Notification escalation (P0 >24h, P1 >48h reminders via bot)
- [x] On-demand scan via Telegram bot command (/scan)
- [x] Dashboard auto-refresh (30-min polling, visibility-aware)
- [x] Analytics (inbox health trend chart, 7d/30d/90d)
- [x] Notion source (comment @mentions + database assignments, hybrid AI/rule-based classification)
- [ ] Discord source (DMs/channels with unanswered messages)
- [ ] GitHub source (issues/PRs assigned or requesting review)
- [ ] Slack source

## Security

Your Telegram messages contain sensitive business data. The system is hardened at every layer:

### VPS (scanner host)
- **Firewall (UFW)** -- only SSH (port 22) allowed inbound, all other ports blocked
- **SSH key-only auth** -- password authentication disabled, root login disabled
- **File permissions** -- session file, .env, OAuth credentials, scan results all chmod 600 (owner-only)
- **No web server** -- scanner runs as a cron job, no exposed HTTP endpoints

### Data handling
- **Session file** (`*.session`) is a Telegram bearer credential. Never commit it. chmod 600 on VPS.
- **All secrets** (API keys, bot token, DB URL) live in `.env` files, never in config.yaml or source code
- **Message content** is not stored verbatim -- only truncated previews and AI-generated summaries go to the database
- **scan_results.json** is gitignored (contains message previews)

### Dashboard (Vercel)
- **Password-protected** -- cookie-based auth with 30-day httpOnly sessions
- **Server Actions** validate UUID inputs before any DB query
- **Middleware** protects all routes except the login page
- **Database** connection uses SSL (Neon enforces `sslmode=require`)

### Reply queue
- **Row locking** (`SELECT FOR UPDATE SKIP LOCKED`) prevents duplicate message sends
- **Server-side chat_id lookup** -- the dashboard never trusts client-provided chat IDs
- **Retry limit** (3 attempts) -- failed sends don't loop forever

## License

MIT
