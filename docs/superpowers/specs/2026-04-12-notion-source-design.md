# Notion Source Integration

## Overview

Add Notion as a source for the catchup-dashboard scanner. Detects comment @mentions and database assignments, classifies them, and displays them on the Kanban dashboard alongside Telegram items.

## Scanning Modes

### 1. Comment @mentions (AI-classified)

For configured parent pages, fetch recent comments via the Notion API. Filter for comments that @mention the user's Notion user ID. These are sent to the Claude classifier alongside Telegram chats for context-aware priority assignment (P0-P3).

### 2. Database assignments (rule-based, P2)

For configured databases, query items where the Assignee property matches the user's Notion user ID and the status is in the configured open statuses (e.g., "Not started", "In progress"). These get a default priority of P2 without AI classification.

## Architecture

### New module: `scanner/src/notion_scanner.py`

- Uses Notion REST API via httpx with bearer token authentication.
- `NOTION_TOKEN` stored in `.env` on VPS.
- API calls:
  - `GET /v1/comments?block_id={page_id}` per monitored page (paginated, filter for @mentions newer than last scan)
  - `POST /v1/databases/{id}/query` per database (filter on assignee + open status)
  - `GET /v1/users/{user_id}` once at startup to resolve display name
- Rate limit safety: 0.5s delay between requests (Notion allows 3 req/s).

### Scanner pipeline integration

- Notion scanning happens in `scanner.py` alongside calendar scanning (step 3b area), before AI classification.
- Comment @mentions are converted to a classifier-compatible format and included in the classification batch.
- Database assignments go directly into the items list with P2 priority (no AI call needed).
- Source is `"notion"` (already defined in Python and TypeScript types).

### Classifier format for comment @mentions

```
--- NOTION PAGE: "Q2 Budget Review" ---
Recent comments mentioning you:
  Matthew Graham (2h ago): "@Emile can you fill in the Mantle section? Need this for the call tomorrow."
  Matthew Graham (1d ago): "@Emile numbers look off in the revenue table, can you double check?"
```

The classifier sees this alongside Telegram chats and assigns priority based on comment content.

## Configuration

In `scanner/config.yaml`:

```yaml
notion:
  enabled: true
  user_id: "your-notion-user-id"
  databases:
    - id: "abc123"
      assignee_property: "Assignee"
      status_property: "Status"
      open_statuses: ["Not started", "In progress"]
  monitor_pages:
    - "def456"
    - "ghi789"
```

- `user_id`: Your Notion user ID (UUID). Found via the Notion API or integration settings.
- `databases`: List of database configs. Each specifies the assignee/status property names and which statuses count as "open."
- `monitor_pages`: List of individual page IDs to scan for comment @mentions. Each page must be shared with the Notion integration.

## Schema Change

Add a generic `source_id` column to `triage_items` for non-Telegram dedup:

```sql
ALTER TABLE triage_items ADD COLUMN IF NOT EXISTS source_id TEXT;
```

This stores the Notion page ID (and can be reused for Discord, GitHub, etc. in the future).

### Dedup

- One triage item per Notion page (keyed by `source_id`).
- Multiple comments on the same page collapse into one item, with the most recent comment as the preview.
- Dashboard dedup query updated to: `DISTINCT ON (COALESCE(chat_id::text, source_id, id::text))`
- Scanner dedup: `get_previous_items` extended to also query by `source_id` for Notion items.

## Data Flow

```
Notion API
  -> notion_scanner.py fetches comments + assignments
  -> Comment @mentions -> classifier batch (AI priority)
  -> Database assignments -> P2 (rule-based)
  -> All items -> push_to_database (source="notion", source_id=page_id)
  -> Dashboard shows with "Notion" source badge (purple, already defined in types.ts)
```

## Authentication

- Create a Notion internal integration at notion.so/my-integrations.
- Share the relevant pages/databases with the integration (Notion requires explicit sharing per page).
- Token stored as `NOTION_TOKEN` in `scanner/.env`.

## Files

### New
- `scanner/src/notion_scanner.py` -- Notion API client, comment fetcher, assignment querier, classifier format converter
- `scanner/tests/test_notion_scanner.py` -- unit tests
- `scanner/migrations/004_add_source_id.sql` -- migration

### Modified
- `scanner/src/config.py` -- add `NotionConfig`
- `scanner/src/scanner.py` -- integrate Notion scanning into pipeline
- `scanner/src/classifier.py` -- accept Notion items in classification batch (format already handled by build_classification_prompt)
- `scanner/src/database.py` -- extend `get_previous_items` and `build_item_insert` for `source_id`
- `scanner/config.yaml` -- add `notion:` section
- `schema.sql` -- add `source_id` column
- `dashboard/lib/db.ts` -- update dedup query for `source_id`

## Testing

- Unit tests for Notion API response parsing, comment filtering, assignment querying
- Unit tests for classifier format conversion
- Unit tests for dedup with source_id
- Integration test: mock Notion API responses through the scanner pipeline
