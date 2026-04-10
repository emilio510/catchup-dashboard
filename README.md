# Catch-up Dashboard

Personal priority tracker that scans your Telegram conversations, classifies them by urgency using AI, and presents them in a Kanban dashboard you can access from anywhere.

**Problem:** You read all your messages but don't always reply. No unread indicator means important conversations fall through the cracks across dozens of active chats.

**Solution:** A scanner reads your Telegram chats, detects who's waiting on a response, classifies priority (P0-P3), and pushes results to a live dashboard with filters, search, and draft replies.

## How It Works

```
Scanner (Python, runs locally)
  Telethon MTProto -> List dialogs -> Filter -> Deep read -> Claude API classification
  -> Push to Postgres + optional Telegram digest

Dashboard (Next.js, deployed on Vercel)
  Reads from Postgres -> Kanban board (P0/P1/P2/P3) -> Mark done / Snooze / Search
```

### Priority Levels

- **P0 -- Respond Today:** Someone is actively blocked, deal-critical, or pinged multiple times
- **P1 -- This Week:** Important deliverable, meeting prep, or time-sensitive request
- **P2 -- Respond:** Question or request, not urgent
- **P3 -- Monitor:** FYI, general discussion, no action needed

When in doubt, the classifier always chooses the higher priority.

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- A Telegram account with API credentials ([my.telegram.org](https://my.telegram.org))
- An Anthropic API key ([console.anthropic.com](https://console.anthropic.com))
- A Neon Postgres database ([neon.tech](https://neon.tech))
- A Vercel account for deployment ([vercel.com](https://vercel.com))

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
SESSION_NAME=your-telegram-username
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require
```

Create `dashboard/.env.local`:

```env
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require
```

### 3. Set up the database

Run the schema against your Neon database. You can use the Neon SQL Editor or any Postgres client:

```sql
-- Copy contents of schema.sql and run it
```

### 4. Configure the scanner

Edit `scanner/config.yaml`:

```yaml
scan:
  window_days: 7          # How far back to scan
  messages_per_chat: 20   # Messages to read per chat
  batch_size: 5           # Chats per Claude API call
  max_dialogs: 50         # Top N most active dialogs to scan

telegram:
  session_name: your-username
  blacklist:              # Chats to skip
    - "News Channel"
    - "Monitoring Alerts"
  bot_whitelist: []       # Bots to include

classification:
  model: claude-sonnet-4-20250514
  max_tokens: 4096
  rate_limit_rpm: 30
  user_context: |
    Describe your role and key collaborators here.
    This helps the AI classify priorities accurately.

output:
  telegram_digest: true   # Send summary to Saved Messages
  json_file: scan_results.json
```

### 5. First scan

```bash
cd scanner
source .venv/bin/activate

# First run will prompt for phone number + 2FA code
python -m src.cli --config config.yaml --no-digest -v
```

This connects to Telegram, scans your chats, classifies them, and pushes results to the database.

### 6. Launch the dashboard

```bash
cd dashboard
pnpm dev
# Open http://localhost:3000
```

### 7. Deploy to Vercel

```bash
cd dashboard
vercel link --yes
vercel env add DATABASE_URL production  # paste your Neon connection string
vercel --prod
```

## Usage

### Daily workflow

```bash
# Run the scanner (takes ~3 min for 50 dialogs)
cd scanner && python -m src.cli --config config.yaml

# Open your dashboard
open https://your-dashboard.vercel.app
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
- **Expandable cards** with context summary and AI-drafted reply
- **Filters** by source, chat type (DM/group), status (open/done/snoozed)
- **Search** across chat names, people, and message previews
- **Mark as done / Snooze** to clear handled items
- **Mobile responsive** -- usable from phone

## Architecture

```
catchup-dashboard/
  scanner/              # Python -- runs locally
    src/
      cli.py            # CLI entry point
      scanner.py        # Orchestrator
      telegram_reader.py # Telethon: list, filter, deep read
      classifier.py     # Claude API batch classification
      digest.py         # Telegram digest formatter
      database.py       # Postgres push (asyncpg)
      config.py         # YAML + env config loader
      models.py         # Pydantic data models
    tests/              # 30 tests
    config.yaml         # Scanner configuration

  dashboard/            # Next.js -- deployed on Vercel
    app/
      page.tsx          # Main page (Server Component)
      actions.ts        # Server Actions (done/snooze)
    components/         # Kanban board, cards, filters
    lib/
      db.ts             # Neon Postgres queries
      types.ts          # Shared TypeScript types

  schema.sql            # Postgres schema
```

### Smart filtering

The scanner applies these filters before classification to reduce noise:

1. **Blacklist** -- skip named chats (configurable in config.yaml)
2. **Channels** -- skip broadcast channels (can't reply anyway)
3. **Bots** -- skip bot chats (unless whitelisted)
4. **You spoke last** -- skip chats where you sent the last message (ball is in their court)
5. **Max dialogs** -- take only the N most recently active chats

### Key design decisions

- **No unread-based filtering:** The scanner detects who's waiting by analyzing message content, not read status. This works even if you read everything and clear notifications.
- **Batch classification:** Chats are sent to Claude in batches of 5 for cost efficiency.
- **Retry with backoff:** API overload errors are retried automatically (3 attempts, exponential backoff).
- **Graceful degradation:** If the database push fails, scan results are still saved to JSON.

## Roadmap

- [ ] Notion source (mentions/tags where your team needs input)
- [ ] GitHub source (issues/PRs assigned or requesting review)
- [ ] Google Calendar (deadlines that boost priority of related chats)
- [ ] Slack source
- [ ] Discord source
- [ ] Deduplication (don't resurface "done" items on re-scan)
- [ ] Cron scheduling (auto-scan every 2h)
- [ ] Authentication on the dashboard

## Security Notes

- **Session file** (`*.session`) is a Telegram bearer credential. Never commit it.
- **API keys** live in `.env` files, never in config.yaml or source code.
- **Scanner is read-only** -- it never sends messages on your behalf (except the optional digest to your own Saved Messages).
- **Message content** is not stored long-term. Only truncated previews and AI summaries go to the database.

## License

MIT
