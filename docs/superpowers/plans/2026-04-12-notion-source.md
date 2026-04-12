# Notion Source Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Notion as a source for the catchup-dashboard scanner, detecting comment @mentions and database assignments.

**Architecture:** New `notion_scanner.py` module uses the Notion REST API (via httpx) to fetch comments and database assignments. Comment @mentions go through the AI classifier; database assignments get rule-based P2 priority. Items are stored with `source="notion"` and deduped by a new `source_id` column (Notion page ID). The dashboard dedup query is updated to use `source_id`.

**Tech Stack:** Python 3.12, httpx (already installed), asyncpg, Notion REST API v1

**IMPORTANT:** After completing each Task, run the code-reviewer agent on the changes. Fix all CRITICAL and HIGH findings. Re-run the reviewer to confirm clean. Only then commit.

---

## File Structure

| File | Responsibility |
|------|---------------|
| `scanner/src/notion_scanner.py` | Notion API client: fetch comments, query assignments, format for classifier, convert to TriageItems |
| `scanner/tests/test_notion_scanner.py` | Unit tests for parsing, filtering, formatting |
| `scanner/src/config.py` | Add `NotionConfig` model |
| `scanner/src/database.py` | Add `source_id` to insert, add `get_previous_notion_items` |
| `scanner/src/models.py` | Add `source_id` field to `TriageItem` |
| `scanner/src/scanner.py` | Wire Notion scanning into pipeline |
| `scanner/config.yaml` | Add `notion:` section |
| `scanner/migrations/004_add_source_id.sql` | Migration |
| `schema.sql` | Add `source_id` column |
| `dashboard/lib/db.ts` | Update dedup query for `source_id` |
| `dashboard/lib/types.ts` | Add `source_id` to `TriageItem` interface |

---

## Task 1: Schema + model changes for `source_id`

**Files:**
- Modify: `schema.sql`
- Create: `scanner/migrations/004_add_source_id.sql`
- Modify: `scanner/src/models.py`
- Modify: `scanner/src/database.py`
- Test: `scanner/tests/test_database.py`

- [ ] **Step 1: Create migration file**

Create `scanner/migrations/004_add_source_id.sql`:

```sql
ALTER TABLE triage_items ADD COLUMN IF NOT EXISTS source_id TEXT;
```

- [ ] **Step 2: Update schema.sql**

In `schema.sql`, add `source_id TEXT` after the `message_id` line (line 31). Change:

```sql
  chat_id          BIGINT,
  message_id       BIGINT,
  user_status      TEXT DEFAULT 'open',
```

To:

```sql
  chat_id          BIGINT,
  message_id       BIGINT,
  source_id        TEXT,
  user_status      TEXT DEFAULT 'open',
```

- [ ] **Step 3: Add `source_id` to TriageItem model**

In `scanner/src/models.py`, add `source_id` field after `message_id`:

```python
class TriageItem(BaseModel):
    source: Source
    chat_name: str
    chat_type: ChatType
    waiting_person: str | None = None
    preview: str
    context_summary: str | None = None
    draft_reply: str | None = None
    priority: Priority
    status: Status = "READ_NO_REPLY"
    tags: list[str] = Field(default_factory=list)
    last_message_at: datetime | None = None
    waiting_since: datetime | None = None
    waiting_days: float | None = None
    chat_id: int | None = None
    message_id: int | None = None
    source_id: str | None = None
```

- [ ] **Step 4: Update `build_item_insert` in database.py to include `source_id`**

In `scanner/src/database.py`, update `build_item_insert`:

```python
def build_item_insert(item: TriageItem, scan_id: str) -> tuple[str, list]:
    query = """
        INSERT INTO triage_items (
            scan_id, source, chat_name, chat_type, waiting_person,
            preview, context_summary, draft_reply, priority, status,
            tags, last_message_at, waiting_since, waiting_days,
            chat_id, message_id, source_id, scanned_at
        ) VALUES (
            $1, $2, $3, $4, $5,
            $6, $7, $8, $9, $10,
            $11, $12, $13, $14,
            $15, $16, $17, $18
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
        item.source_id,
        datetime.now(timezone.utc),
    ]
    return query, params
```

- [ ] **Step 5: Add `get_previous_notion_items` to database.py**

Add after `get_previous_items`:

```python
async def get_previous_notion_items(database_url: str, source_ids: list[str]) -> dict[str, dict]:
    """Get the most recent triage item per source_id for Notion dedup."""
    if not source_ids:
        return {}
    conn = await asyncpg.connect(database_url)
    try:
        rows = await conn.fetch("""
            SELECT DISTINCT ON (source_id)
                id, source_id, scanned_at, user_status, last_message_at,
                priority, status, preview, context_summary
            FROM triage_items
            WHERE source_id = ANY($1)
              AND source = 'notion'
            ORDER BY source_id, scanned_at DESC
        """, source_ids)
        return {
            row["source_id"]: {
                "id": str(row["id"]),
                "scanned_at": row["scanned_at"],
                "user_status": row["user_status"],
                "last_message_at": row["last_message_at"],
                "priority": row["priority"],
                "status": row["status"],
                "preview": row["preview"],
                "context_summary": row["context_summary"],
            }
            for row in rows
        }
    finally:
        await conn.close()
```

- [ ] **Step 6: Update test for build_item_insert**

In `scanner/tests/test_database.py`, update `test_build_item_insert` to include `source_id`:

```python
def test_build_item_insert():
    item = TriageItem(
        source="telegram", chat_name="Logic Protocol Core", chat_type="group",
        waiting_person="Marc", preview="What about the vault params?",
        context_summary="Marc asking about vault params", draft_reply="Hey Marc...",
        priority="P0", status="READ_NO_REPLY", tags=["deal blocker"],
        last_message_at=datetime(2026, 4, 7, 14, 0, tzinfo=timezone.utc),
        waiting_since=datetime(2026, 4, 7, 14, 0, tzinfo=timezone.utc),
        waiting_days=3, chat_id=-100123, message_id=42,
    )
    query, params = build_item_insert(item, "550e8400-e29b-41d4-a716-446655440000")
    assert "INSERT INTO triage_items" in query
    assert "source_id" in query
    assert params[0] == "550e8400-e29b-41d4-a716-446655440000"
    assert params[1] == "telegram"
    assert params[2] == "Logic Protocol Core"
    assert params[4] == "Marc"
    assert params[8] == "P0"
    assert params[10] == ["deal blocker"]
    assert params[16] is None  # source_id is None for telegram items


def test_build_item_insert_with_source_id():
    item = TriageItem(
        source="notion", chat_name="Q2 Budget Review", chat_type="dm",
        preview="@Emile fill in the Mantle section",
        priority="P1", status="NEW",
        source_id="abc-123-page-id",
    )
    query, params = build_item_insert(item, "550e8400-e29b-41d4-a716-446655440000")
    assert params[16] == "abc-123-page-id"
```

- [ ] **Step 7: Run tests**

Run: `cd /Users/akgemilio/Projects/catchup-dashboard/scanner && python3 -m pytest tests/test_database.py tests/test_models.py -v`
Expected: All PASS

- [ ] **Step 8: Run code-reviewer, fix findings, re-review, then commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add schema.sql scanner/migrations/004_add_source_id.sql scanner/src/models.py scanner/src/database.py scanner/tests/test_database.py
git commit -m "feat(notion): add source_id column for non-Telegram source dedup"
```

---

## Task 2: NotionConfig and config.yaml

**Files:**
- Modify: `scanner/src/config.py`
- Modify: `scanner/config.yaml`
- Test: `scanner/tests/test_config.py`

- [ ] **Step 1: Add NotionConfig to config.py**

In `scanner/src/config.py`, add after `EscalationConfig`:

```python
class NotionDatabaseConfig(BaseModel):
    id: str
    assignee_property: str = "Assignee"
    status_property: str = "Status"
    open_statuses: list[str] = Field(default_factory=lambda: ["Not started", "In progress"])


class NotionConfig(BaseModel):
    enabled: bool = False
    user_id: str = ""
    token: str = ""  # Set via NOTION_TOKEN env var
    databases: list[NotionDatabaseConfig] = Field(default_factory=list)
    monitor_pages: list[str] = Field(default_factory=list)
```

- [ ] **Step 2: Add notion field to ScannerConfig**

```python
class ScannerConfig(BaseModel):
    scan: ScanConfig = Field(default_factory=ScanConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    classification: ClassificationConfig = Field(default_factory=ClassificationConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    calendar: CalendarConfig = Field(default_factory=CalendarConfig)
    escalation: EscalationConfig = Field(default_factory=EscalationConfig)
    notion: NotionConfig = Field(default_factory=NotionConfig)
```

- [ ] **Step 3: Add NOTION_TOKEN env var overlay in `from_yaml`**

In the `from_yaml` method, add after the output env var block (before `config = cls(**data)`):

```python
        notion_data = data.get("notion", {})
        notion_token = os.environ.get("NOTION_TOKEN", "")
        if notion_token:
            notion_data["token"] = notion_token
        data["notion"] = notion_data
```

- [ ] **Step 4: Add notion section to config.yaml**

Add at the end of `scanner/config.yaml`:

```yaml

notion:
  enabled: false
  user_id: ""  # Your Notion user ID (UUID)
  # token: set via NOTION_TOKEN env var
  databases: []
    # - id: "database-uuid"
    #   assignee_property: "Assignee"
    #   status_property: "Status"
    #   open_statuses: ["Not started", "In progress"]
  monitor_pages: []
    # - "page-uuid-1"
    # - "page-uuid-2"
```

- [ ] **Step 5: Write config tests**

In `scanner/tests/test_config.py`, add:

```python
def test_notion_config_defaults():
    from src.config import NotionConfig
    config = NotionConfig()
    assert config.enabled is False
    assert config.user_id == ""
    assert config.databases == []
    assert config.monitor_pages == []


def test_notion_config_from_yaml(tmp_path):
    from src.config import ScannerConfig
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
telegram:
  blacklist: []
notion:
  enabled: true
  user_id: "user-uuid-123"
  databases:
    - id: "db-uuid-456"
      assignee_property: "Owner"
      status_property: "State"
      open_statuses: ["Todo", "Doing"]
  monitor_pages:
    - "page-uuid-789"
""")
    import os
    os.environ.setdefault("TELEGRAM_API_ID", "12345")
    os.environ.setdefault("TELEGRAM_API_HASH", "test_hash")
    os.environ.setdefault("ANTHROPIC_API_KEY", "test_key")
    config = ScannerConfig.from_yaml(config_file)
    assert config.notion.enabled is True
    assert config.notion.user_id == "user-uuid-123"
    assert len(config.notion.databases) == 1
    assert config.notion.databases[0].id == "db-uuid-456"
    assert config.notion.databases[0].assignee_property == "Owner"
    assert config.notion.databases[0].open_statuses == ["Todo", "Doing"]
    assert config.notion.monitor_pages == ["page-uuid-789"]


def test_notion_token_from_env(tmp_path):
    from src.config import ScannerConfig
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
telegram:
  blacklist: []
notion:
  enabled: true
  user_id: "user-uuid"
""")
    import os
    os.environ["NOTION_TOKEN"] = "ntn_test_token_123"
    os.environ.setdefault("TELEGRAM_API_ID", "12345")
    os.environ.setdefault("TELEGRAM_API_HASH", "test_hash")
    os.environ.setdefault("ANTHROPIC_API_KEY", "test_key")
    try:
        config = ScannerConfig.from_yaml(config_file)
        assert config.notion.token == "ntn_test_token_123"
    finally:
        del os.environ["NOTION_TOKEN"]
```

- [ ] **Step 6: Run tests**

Run: `cd /Users/akgemilio/Projects/catchup-dashboard/scanner && python3 -m pytest tests/test_config.py -v`
Expected: All PASS

- [ ] **Step 7: Run code-reviewer, fix findings, re-review, then commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add scanner/src/config.py scanner/config.yaml scanner/tests/test_config.py
git commit -m "feat(notion): add NotionConfig with databases and monitor_pages"
```

---

## Task 3: Notion scanner module -- API client and data types

**Files:**
- Create: `scanner/src/notion_scanner.py`
- Create: `scanner/tests/test_notion_scanner.py`

- [ ] **Step 1: Write failing tests for Notion API response parsing**

Create `scanner/tests/test_notion_scanner.py`:

```python
from datetime import datetime, timezone
from src.notion_scanner import (
    parse_comments_response,
    parse_database_query_response,
    filter_mentions,
    format_notion_items_for_classifier,
    comments_to_triage_items,
    assignments_to_triage_items,
)


MOCK_COMMENTS_RESPONSE = {
    "results": [
        {
            "id": "comment-1",
            "created_time": "2026-04-12T10:00:00.000Z",
            "created_by": {"id": "boss-user-id"},
            "rich_text": [
                {"type": "text", "text": {"content": "Hey "}},
                {"type": "mention", "mention": {"type": "user", "user": {"id": "my-user-id"}}},
                {"type": "text", "text": {"content": " can you fill in the Mantle section?"}},
            ],
            "parent": {"type": "page_id", "page_id": "page-abc"},
        },
        {
            "id": "comment-2",
            "created_time": "2026-04-12T08:00:00.000Z",
            "created_by": {"id": "other-user-id"},
            "rich_text": [
                {"type": "text", "text": {"content": "Looks good to me"}},
            ],
            "parent": {"type": "page_id", "page_id": "page-abc"},
        },
    ],
    "has_more": False,
}


def test_parse_comments_response():
    comments = parse_comments_response(MOCK_COMMENTS_RESPONSE)
    assert len(comments) == 2
    assert comments[0]["id"] == "comment-1"
    assert comments[0]["created_by_id"] == "boss-user-id"
    assert "Mantle section" in comments[0]["text"]


def test_filter_mentions():
    comments = parse_comments_response(MOCK_COMMENTS_RESPONSE)
    mentioned = filter_mentions(comments, "my-user-id")
    assert len(mentioned) == 1
    assert mentioned[0]["id"] == "comment-1"


def test_filter_mentions_no_match():
    comments = parse_comments_response(MOCK_COMMENTS_RESPONSE)
    mentioned = filter_mentions(comments, "nobody-id")
    assert len(mentioned) == 0


MOCK_DB_QUERY_RESPONSE = {
    "results": [
        {
            "id": "page-xyz",
            "url": "https://notion.so/page-xyz",
            "properties": {
                "Name": {"title": [{"text": {"content": "Write Q2 report"}}]},
                "Assignee": {"people": [{"id": "my-user-id"}]},
                "Status": {"status": {"name": "In progress"}},
            },
            "last_edited_time": "2026-04-11T14:00:00.000Z",
        },
    ],
    "has_more": False,
}


def test_parse_database_query_response():
    items = parse_database_query_response(
        MOCK_DB_QUERY_RESPONSE,
        title_property="Name",
        assignee_property="Assignee",
        status_property="Status",
    )
    assert len(items) == 1
    assert items[0]["page_id"] == "page-xyz"
    assert items[0]["title"] == "Write Q2 report"
    assert items[0]["status"] == "In progress"


def test_assignments_to_triage_items():
    assignments = [{
        "page_id": "page-xyz",
        "title": "Write Q2 report",
        "status": "In progress",
        "last_edited": "2026-04-11T14:00:00.000Z",
        "url": "https://notion.so/page-xyz",
    }]
    items = assignments_to_triage_items(assignments)
    assert len(items) == 1
    assert items[0].source == "notion"
    assert items[0].priority == "P2"
    assert items[0].source_id == "page-xyz"
    assert items[0].chat_name == "Write Q2 report"


def test_format_notion_items_for_classifier():
    mention_groups = {
        "Q2 Budget Review": {
            "page_id": "page-abc",
            "comments": [
                {
                    "created_by_name": "Matthew Graham",
                    "text": "can you fill in the Mantle section?",
                    "created_time": "2026-04-12T10:00:00.000Z",
                },
            ],
        },
    }
    text = format_notion_items_for_classifier(mention_groups)
    assert "NOTION PAGE" in text
    assert "Q2 Budget Review" in text
    assert "Matthew Graham" in text
    assert "Mantle section" in text


def test_comments_to_triage_items():
    mention_groups = {
        "Q2 Budget Review": {
            "page_id": "page-abc",
            "comments": [
                {
                    "created_by_name": "Matthew Graham",
                    "text": "can you fill in the Mantle section?",
                    "created_time": "2026-04-12T10:00:00.000Z",
                },
            ],
        },
    }
    items = comments_to_triage_items(mention_groups)
    assert len(items) == 1
    assert items[0].source == "notion"
    assert items[0].source_id == "page-abc"
    assert items[0].chat_name == "Q2 Budget Review"
    assert items[0].priority == "P1"  # default for comment mentions
    assert "Matthew Graham" in items[0].preview
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/akgemilio/Projects/catchup-dashboard/scanner && python3 -m pytest tests/test_notion_scanner.py -v`
Expected: FAIL -- module not found

- [ ] **Step 3: Implement notion_scanner.py**

Create `scanner/src/notion_scanner.py`:

```python
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import httpx

from src.config import ScannerConfig
from src.models import TriageItem

logger = logging.getLogger(__name__)

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
REQUEST_DELAY = 0.5  # seconds between API calls


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _extract_text(rich_text_list: list[dict]) -> str:
    """Extract plain text from Notion rich_text array."""
    parts = []
    for block in rich_text_list:
        if block.get("type") == "text":
            parts.append(block.get("text", {}).get("content", ""))
        elif block.get("type") == "mention":
            mention = block.get("mention", {})
            if mention.get("type") == "user":
                parts.append(f"@user")
    return "".join(parts)


def _extract_mentioned_user_ids(rich_text_list: list[dict]) -> list[str]:
    """Extract user IDs from mention blocks in rich_text."""
    ids = []
    for block in rich_text_list:
        if block.get("type") == "mention":
            mention = block.get("mention", {})
            if mention.get("type") == "user":
                user_id = mention.get("user", {}).get("id")
                if user_id:
                    ids.append(user_id)
    return ids


def parse_comments_response(data: dict) -> list[dict]:
    """Parse Notion comments API response into a flat list of comment dicts."""
    comments = []
    for result in data.get("results", []):
        rich_text = result.get("rich_text", [])
        comments.append({
            "id": result["id"],
            "created_time": result["created_time"],
            "created_by_id": result.get("created_by", {}).get("id", ""),
            "text": _extract_text(rich_text),
            "mentioned_user_ids": _extract_mentioned_user_ids(rich_text),
            "parent_page_id": result.get("parent", {}).get("page_id", ""),
        })
    return comments


def filter_mentions(comments: list[dict], user_id: str) -> list[dict]:
    """Filter comments to only those that @mention the given user ID."""
    return [c for c in comments if user_id in c["mentioned_user_ids"]]


def parse_database_query_response(
    data: dict,
    title_property: str = "Name",
    assignee_property: str = "Assignee",
    status_property: str = "Status",
) -> list[dict]:
    """Parse Notion database query response into assignment dicts."""
    items = []
    for result in data.get("results", []):
        props = result.get("properties", {})

        # Extract title
        title_prop = props.get(title_property, {})
        title_parts = title_prop.get("title", [])
        title = "".join(p.get("text", {}).get("content", "") for p in title_parts) or "Untitled"

        # Extract status
        status_prop = props.get(status_property, {})
        status_data = status_prop.get("status") or status_prop.get("select")
        status_name = status_data.get("name", "") if status_data else ""

        items.append({
            "page_id": result["id"],
            "title": title,
            "status": status_name,
            "last_edited": result.get("last_edited_time", ""),
            "url": result.get("url", ""),
        })
    return items


def assignments_to_triage_items(assignments: list[dict]) -> list[TriageItem]:
    """Convert database assignments to TriageItems with rule-based P2 priority."""
    items = []
    for assignment in assignments:
        items.append(TriageItem(
            source="notion",
            chat_name=assignment["title"],
            chat_type="dm",
            waiting_person=None,
            preview=f"Assigned to you -- status: {assignment['status']}",
            context_summary=f"Database task assigned to you, currently {assignment['status']}",
            draft_reply=None,
            priority="P2",
            status="NEW",
            tags=["notion", "assigned"],
            last_message_at=_parse_iso(assignment.get("last_edited")),
            waiting_since=_parse_iso(assignment.get("last_edited")),
            waiting_days=None,
            chat_id=None,
            message_id=None,
            source_id=assignment["page_id"],
        ))
    return items


def format_notion_items_for_classifier(mention_groups: dict[str, dict]) -> str:
    """Format Notion comment @mentions for the AI classifier.

    mention_groups: {page_title: {page_id, comments: [{created_by_name, text, created_time}]}}
    """
    if not mention_groups:
        return ""

    parts = []
    for page_title, group in mention_groups.items():
        parts.append(f"--- NOTION PAGE: \"{page_title}\" ---")
        parts.append("Recent comments mentioning you:")
        for comment in group["comments"]:
            name = comment["created_by_name"]
            text = comment["text"]
            time = comment["created_time"]
            try:
                dt = datetime.fromisoformat(time.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                hours_ago = (now - dt).total_seconds() / 3600
                if hours_ago < 1:
                    time_label = "just now"
                elif hours_ago < 24:
                    time_label = f"{int(hours_ago)}h ago"
                else:
                    time_label = f"{int(hours_ago / 24)}d ago"
            except (ValueError, TypeError):
                time_label = time
            parts.append(f"  {name} ({time_label}): \"{text}\"")
        parts.append("")

    return "\n".join(parts)


def comments_to_triage_items(mention_groups: dict[str, dict]) -> list[TriageItem]:
    """Convert comment mention groups to TriageItems with default P1 (AI will reclassify)."""
    items = []
    for page_title, group in mention_groups.items():
        latest_comment = group["comments"][0] if group["comments"] else None
        if not latest_comment:
            continue

        preview_text = f"{latest_comment['created_by_name']}: {latest_comment['text']}"

        items.append(TriageItem(
            source="notion",
            chat_name=page_title,
            chat_type="dm",
            waiting_person=latest_comment["created_by_name"],
            preview=preview_text[:200],
            context_summary=None,  # Will be set by classifier
            draft_reply=None,
            priority="P1",  # Default, classifier will override
            status="NEW",
            tags=["notion", "mention"],
            last_message_at=_parse_iso(latest_comment.get("created_time")),
            waiting_since=_parse_iso(latest_comment.get("created_time")),
            waiting_days=None,
            chat_id=None,
            message_id=None,
            source_id=group["page_id"],
        ))
    return items


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


async def fetch_page_title(http: httpx.AsyncClient, token: str, page_id: str) -> str:
    """Fetch the title of a Notion page."""
    try:
        resp = await http.get(
            f"{NOTION_API_BASE}/pages/{page_id}",
            headers=_headers(token),
        )
        if not resp.is_success:
            logger.error("Failed to fetch page %s: status %d", page_id, resp.status_code)
            return "Untitled"
        data = resp.json()
        props = data.get("properties", {})
        # Try common title property names
        for key in ["Name", "Title", "title"]:
            if key in props:
                title_parts = props[key].get("title", [])
                title = "".join(p.get("text", {}).get("content", "") for p in title_parts)
                if title:
                    return title
        return "Untitled"
    except httpx.HTTPError:
        logger.error("HTTP error fetching page title for %s", page_id)
        return "Untitled"


async def fetch_user_name(http: httpx.AsyncClient, token: str, user_id: str) -> str:
    """Fetch a Notion user's display name."""
    try:
        resp = await http.get(
            f"{NOTION_API_BASE}/users/{user_id}",
            headers=_headers(token),
        )
        if resp.is_success:
            return resp.json().get("name", "Unknown")
        return "Unknown"
    except httpx.HTTPError:
        return "Unknown"


async def fetch_comments_for_page(
    http: httpx.AsyncClient,
    token: str,
    page_id: str,
) -> list[dict]:
    """Fetch all comments on a Notion page (paginated)."""
    all_comments: list[dict] = []
    cursor = None

    while True:
        params: dict[str, str] = {"block_id": page_id}
        if cursor:
            params["start_cursor"] = cursor

        try:
            resp = await http.get(
                f"{NOTION_API_BASE}/comments",
                headers=_headers(token),
                params=params,
            )
        except httpx.HTTPError:
            logger.error("HTTP error fetching comments for page %s", page_id)
            break

        if not resp.is_success:
            logger.error("Failed to fetch comments for page %s: status %d", page_id, resp.status_code)
            break

        data = resp.json()
        all_comments.extend(parse_comments_response(data))

        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")

        await asyncio.sleep(REQUEST_DELAY)

    return all_comments


async def query_database_assignments(
    http: httpx.AsyncClient,
    token: str,
    database_id: str,
    user_id: str,
    assignee_property: str,
    status_property: str,
    open_statuses: list[str],
) -> list[dict]:
    """Query a Notion database for items assigned to the user with open status."""
    # Build filter: assignee contains user AND status is in open_statuses
    status_filters = [
        {"property": status_property, "status": {"equals": status}}
        for status in open_statuses
    ]

    filter_body: dict = {
        "and": [
            {"property": assignee_property, "people": {"contains": user_id}},
            {"or": status_filters} if len(status_filters) > 1 else status_filters[0],
        ]
    }

    try:
        resp = await http.post(
            f"{NOTION_API_BASE}/databases/{database_id}/query",
            headers=_headers(token),
            json={"filter": filter_body},
        )
    except httpx.HTTPError:
        logger.error("HTTP error querying database %s", database_id)
        return []

    if not resp.is_success:
        logger.error("Failed to query database %s: status %d", database_id, resp.status_code)
        return []

    return parse_database_query_response(
        resp.json(),
        title_property="Name",
        assignee_property=assignee_property,
        status_property=status_property,
    )


async def scan_notion(config: ScannerConfig) -> tuple[list[TriageItem], dict[str, dict]]:
    """Scan Notion for comment @mentions and database assignments.

    Returns:
        (rule_based_items, mention_groups_for_classifier)
        - rule_based_items: TriageItems with P2 priority (database assignments)
        - mention_groups_for_classifier: dict to pass to format_notion_items_for_classifier,
          then to the AI classifier. After classification, use comments_to_triage_items
          for any items not handled by the classifier.
    """
    if not config.notion.enabled:
        return [], {}

    token = config.notion.token
    user_id = config.notion.user_id

    if not token or not user_id:
        logger.warning("Notion enabled but token or user_id not configured")
        return [], {}

    rule_based_items: list[TriageItem] = []
    mention_groups: dict[str, dict] = {}

    # Cache user names to avoid repeated API calls
    user_name_cache: dict[str, str] = {}

    async with httpx.AsyncClient(timeout=10.0) as http:
        # 1. Scan configured databases for assignments
        for db_config in config.notion.databases:
            await asyncio.sleep(REQUEST_DELAY)
            assignments = await query_database_assignments(
                http, token, db_config.id, user_id,
                db_config.assignee_property,
                db_config.status_property,
                db_config.open_statuses,
            )
            rule_based_items.extend(assignments_to_triage_items(assignments))
            logger.info("Notion DB %s: %d assignments", db_config.id[:8], len(assignments))

        # 2. Scan monitored pages for comment @mentions
        for page_id in config.notion.monitor_pages:
            await asyncio.sleep(REQUEST_DELAY)
            comments = await fetch_comments_for_page(http, token, page_id)
            mentioned = filter_mentions(comments, user_id)

            if not mentioned:
                continue

            # Resolve page title
            page_title = await fetch_page_title(http, token, page_id)

            # Resolve comment author names
            enriched_comments = []
            for comment in mentioned:
                author_id = comment["created_by_id"]
                if author_id not in user_name_cache:
                    await asyncio.sleep(REQUEST_DELAY)
                    user_name_cache[author_id] = await fetch_user_name(http, token, author_id)
                enriched_comments.append({
                    "created_by_name": user_name_cache[author_id],
                    "text": comment["text"],
                    "created_time": comment["created_time"],
                })

            # Sort by most recent first
            enriched_comments.sort(key=lambda c: c["created_time"], reverse=True)

            mention_groups[page_title] = {
                "page_id": page_id,
                "comments": enriched_comments,
            }
            logger.info("Notion page '%s': %d comments mentioning you", page_title, len(enriched_comments))

    return rule_based_items, mention_groups
```

- [ ] **Step 4: Run tests**

Run: `cd /Users/akgemilio/Projects/catchup-dashboard/scanner && python3 -m pytest tests/test_notion_scanner.py -v`
Expected: All PASS

- [ ] **Step 5: Run full test suite**

Run: `cd /Users/akgemilio/Projects/catchup-dashboard/scanner && python3 -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 6: Run code-reviewer, fix findings, re-review, then commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add scanner/src/notion_scanner.py scanner/tests/test_notion_scanner.py
git commit -m "feat(notion): add Notion scanner module -- comments, assignments, API client"
```

---

## Task 4: Wire Notion into scanner pipeline

**Files:**
- Modify: `scanner/src/scanner.py`

- [ ] **Step 1: Add Notion imports to scanner.py**

At the top of `scanner/src/scanner.py`, add:

```python
from src.notion_scanner import (
    scan_notion,
    format_notion_items_for_classifier,
    comments_to_triage_items,
)
```

- [ ] **Step 2: Add Notion scanning step after calendar scanning**

In `scanner/src/scanner.py`, after the calendar scanning block (around line 130, after the `except Exception` for calendar), add:

```python
            # 3c. Fetch Notion items (if enabled)
            notion_rule_items: list[TriageItem] = []
            notion_mention_groups: dict[str, dict] = {}
            if self._config.notion.enabled:
                try:
                    notion_rule_items, notion_mention_groups = await scan_notion(self._config)
                    if notion_mention_groups:
                        self._classifier.notion_context = format_notion_items_for_classifier(notion_mention_groups)
                    logger.info(
                        "Notion: %d assignments, %d pages with mentions",
                        len(notion_rule_items), len(notion_mention_groups),
                    )
                except Exception:
                    logger.exception("Failed to fetch Notion items (continuing without)")
```

- [ ] **Step 3: Add `notion_context` to Classifier class**

In `scanner/src/classifier.py`, add `self.notion_context: str = ""` in `__init__` (next to `self.calendar_context`).

Then in `build_classification_prompt`, add after the calendar_context block:

```python
    if notion_context:
        parts.append(notion_context)
        parts.append("")
```

Update the function signature to accept `notion_context: str = ""` and update `classify_batch` to pass it.

Actually, simpler approach: the `notion_context` is already set on `self._classifier.notion_context`. Just include it in the prompt building. Add to `classify_batch`:

```python
        prompt = build_classification_prompt(
            conversations,
            my_display_name,
            self._config.classification.user_context,
            calendar_context=self.calendar_context,
            previous_context=previous_context,
            notion_context=self.notion_context,
        )
```

And update `build_classification_prompt` signature:

```python
def build_classification_prompt(
    conversations: list[ConversationData],
    my_display_name: str,
    user_context: str,
    calendar_context: str = "",
    previous_context: dict[str, dict] | None = None,
    notion_context: str = "",
) -> str:
```

Add after the calendar context block in the function body:

```python
    if notion_context:
        parts.append(notion_context)
        parts.append("")
```

- [ ] **Step 4: Include Notion items in the result**

In `scanner/src/scanner.py`, where items are assembled (around line 175-180), add Notion items:

```python
            # 6. Add calendar + Notion items + sort by priority
            items.extend(calendar_items)
            items.extend(notion_rule_items)
            if notion_mention_groups:
                items.extend(comments_to_triage_items(notion_mention_groups))
```

Also update the sources list:

```python
            sources = ["telegram"]
            if calendar_events:
                sources.append("calendar")
            if notion_rule_items or notion_mention_groups:
                sources.append("notion")
```

- [ ] **Step 5: Handle the dedup early-return path**

In the early-return path (around line 122-156, where `if not conversations:` after dedup), also include Notion items:

```python
                all_items = calendar_items + notion_rule_items
                if notion_mention_groups:
                    all_items.extend(comments_to_triage_items(notion_mention_groups))
```

And update sources in that path:

```python
                sources = ["telegram"]
                if calendar_items:
                    sources.append("calendar")
                if notion_rule_items or notion_mention_groups:
                    sources.append("notion")
```

- [ ] **Step 6: Run full test suite**

Run: `cd /Users/akgemilio/Projects/catchup-dashboard/scanner && python3 -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 7: Run code-reviewer, fix findings, re-review, then commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add scanner/src/scanner.py scanner/src/classifier.py
git commit -m "feat(notion): wire Notion scanning into scanner pipeline"
```

---

## Task 5: Dashboard dedup query update

**Files:**
- Modify: `dashboard/lib/db.ts`
- Modify: `dashboard/lib/types.ts`

- [ ] **Step 1: Add `source_id` to TypeScript TriageItem interface**

In `dashboard/lib/types.ts`, add after `message_id`:

```typescript
  source_id: string | null;
```

- [ ] **Step 2: Update dedup query in getTriageItems**

In `dashboard/lib/db.ts`, update the DISTINCT ON clause in `getTriageItems`. Change:

```sql
SELECT DISTINCT ON (COALESCE(chat_id::text, id::text)) *
```

To:

```sql
SELECT DISTINCT ON (COALESCE(chat_id::text, source_id, id::text)) *
```

And update the ORDER BY to match:

```sql
ORDER BY COALESCE(chat_id::text, source_id, id::text), scanned_at DESC
```

- [ ] **Step 3: Update analytics query to include Notion items**

In `dashboard/lib/db.ts`, in `getAnalyticsData`, change the source filter from:

```sql
AND ti.source = 'telegram'
```

To:

```sql
AND ti.source IN ('telegram', 'notion')
```

- [ ] **Step 4: Build the dashboard**

Run: `cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && npm run build`
Expected: Build succeeds

- [ ] **Step 5: Run code-reviewer, fix findings, re-review, then commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/lib/db.ts dashboard/lib/types.ts
git commit -m "feat(notion): update dashboard dedup query and types for source_id"
```

---

## Task 6: Run migration and final verification

- [ ] **Step 1: Run migration on Neon**

Add to `scanner/migrations/run_migrations.py`:

```python
        await conn.execute(
            "ALTER TABLE triage_items ADD COLUMN IF NOT EXISTS source_id TEXT"
        )
        print("004: source_id column added")
```

Run: `cd /Users/akgemilio/Projects/catchup-dashboard/scanner && python3 -m migrations.run_migrations`

- [ ] **Step 2: Run full Python test suite**

Run: `cd /Users/akgemilio/Projects/catchup-dashboard/scanner && python3 -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 3: Build dashboard**

Run: `cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && npm run build`
Expected: Build succeeds

- [ ] **Step 4: Run final code-reviewer on full changeset**

Review all modified files since the session started. Verify no CRITICAL or HIGH findings.

- [ ] **Step 5: Commit migration update and push**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add scanner/migrations/run_migrations.py
git commit -m "chore: add source_id migration to runner"
git push
```
