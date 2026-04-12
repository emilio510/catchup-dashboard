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
REQUEST_DELAY = 0.5


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

def _extract_text(rich_text: list[dict]) -> tuple[str, list[str]]:
    """Return (plain_text, mentioned_user_ids) from a rich_text block list."""
    parts: list[str] = []
    mentioned: list[str] = []
    for block in rich_text:
        block_type = block.get("type", "")
        if block_type == "text":
            parts.append(block.get("text", {}).get("content", ""))
        elif block_type == "mention":
            mention = block.get("mention", {})
            if mention.get("type") == "user":
                user_id = mention.get("user", {}).get("id", "")
                if user_id:
                    mentioned.append(user_id)
                parts.append("@user")
            else:
                parts.append("")
        else:
            parts.append("")
    return "".join(parts), mentioned


def parse_comments_response(data: dict) -> list[dict]:
    """Parse Notion comments API response into a list of comment dicts."""
    comments: list[dict] = []
    for result in data.get("results", []):
        rich_text = result.get("rich_text", [])
        text, mentioned_user_ids = _extract_text(rich_text)
        parent = result.get("parent", {})
        parent_page_id = parent.get("page_id", "") if parent.get("type") == "page_id" else ""
        comments.append({
            "id": result.get("id", ""),
            "created_time": result.get("created_time", ""),
            "created_by_id": result.get("created_by", {}).get("id", ""),
            "text": text,
            "mentioned_user_ids": mentioned_user_ids,
            "parent_page_id": parent_page_id,
        })
    return comments


def filter_mentions(comments: list[dict], user_id: str) -> list[dict]:
    """Return only comments that @mention the given user ID."""
    return [c for c in comments if user_id in c.get("mentioned_user_ids", [])]


def parse_database_query_response(
    data: dict,
    title_property: str,
    assignee_property: str,
    status_property: str,
) -> list[dict]:
    """Parse Notion database query response into assignment dicts."""
    items: list[dict] = []
    for result in data.get("results", []):
        props = result.get("properties", {})

        # Title
        title_prop = props.get(title_property, {})
        title_blocks = title_prop.get("title", [])
        title = "".join(b.get("text", {}).get("content", "") for b in title_blocks)

        # Status
        status_prop = props.get(status_property, {})
        status = ""
        if "status" in status_prop and status_prop["status"]:
            status = status_prop["status"].get("name", "")

        items.append({
            "page_id": result.get("id", ""),
            "title": title,
            "status": status,
            "last_edited": result.get("last_edited_time", ""),
            "url": result.get("url", ""),
        })
    return items


def assignments_to_triage_items(assignments: list[dict]) -> list[TriageItem]:
    """Convert assignment dicts to TriageItems (rule-based, P2)."""
    items: list[TriageItem] = []
    for a in assignments:
        items.append(TriageItem(
            source="notion",
            chat_name=a.get("title", "Untitled"),
            chat_type="group",
            waiting_person=None,
            preview=f"Status: {a.get('status', 'Unknown')} -- {a.get('url', '')}",
            priority="P2",
            status="NEW",
            tags=["notion", "assignment"],
            source_id=a.get("page_id"),
        ))
    return items


def _format_relative_time(created_time: str) -> str:
    """Return a human-readable relative time string like '2h ago'."""
    try:
        dt = datetime.fromisoformat(created_time.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - dt
        total_seconds = int(delta.total_seconds())
        if total_seconds < 60:
            return "just now"
        if total_seconds < 3600:
            return f"{total_seconds // 60}m ago"
        if total_seconds < 86400:
            return f"{total_seconds // 3600}h ago"
        return f"{total_seconds // 86400}d ago"
    except (ValueError, TypeError):
        return created_time


def format_notion_items_for_classifier(mention_groups: dict[str, dict]) -> str:
    """Format @mention groups for the AI classifier prompt."""
    if not mention_groups:
        return ""
    lines: list[str] = []
    for page_title, group in mention_groups.items():
        lines.append(f'--- NOTION PAGE: "{page_title}" ---')
        lines.append("Recent comments mentioning you:")
        for comment in group.get("comments", []):
            author = comment.get("created_by_name", "Unknown")
            text = comment.get("text", "")
            when = _format_relative_time(comment.get("created_time", ""))
            lines.append(f'  {author} ({when}): "{text}"')
    return "\n".join(lines)


def comments_to_triage_items(mention_groups: dict[str, dict]) -> list[TriageItem]:
    """Convert mention groups to TriageItems (P1, classifier will override)."""
    items: list[TriageItem] = []
    for page_title, group in mention_groups.items():
        comments = group.get("comments", [])
        if not comments:
            continue
        # Build preview from the first comment
        first = comments[0]
        author = first.get("created_by_name", "Unknown")
        text = first.get("text", "")
        preview = f"{author}: {text}"
        if len(comments) > 1:
            preview += f" (+{len(comments) - 1} more)"

        items.append(TriageItem(
            source="notion",
            chat_name=page_title,
            chat_type="group",
            waiting_person=author,
            preview=preview,
            priority="P1",
            status="NEW",
            tags=["notion", "mention"],
            source_id=group.get("page_id"),
        ))
    return items


# ---------------------------------------------------------------------------
# Async API helpers
# ---------------------------------------------------------------------------

def _notion_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


async def fetch_page_title(http: httpx.AsyncClient, token: str, page_id: str) -> str:
    """Fetch a page's title from the Notion API."""
    try:
        resp = await http.get(
            f"{NOTION_API_BASE}/pages/{page_id}",
            headers=_notion_headers(token),
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        props = data.get("properties", {})
        # Try common title property names
        for key in ("Name", "Title", "title"):
            prop = props.get(key, {})
            blocks = prop.get("title", [])
            if blocks:
                return "".join(b.get("text", {}).get("content", "") for b in blocks)
        return page_id
    except httpx.HTTPError as exc:
        logger.error("Failed to fetch page title for %s: %s", page_id, type(exc).__name__)
        return page_id


async def fetch_user_name(http: httpx.AsyncClient, token: str, user_id: str) -> str:
    """Fetch a user's display name from the Notion API."""
    try:
        resp = await http.get(
            f"{NOTION_API_BASE}/users/{user_id}",
            headers=_notion_headers(token),
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("name") or data.get("id", user_id)
    except httpx.HTTPError as exc:
        logger.error("Failed to fetch user name for %s: %s", user_id, type(exc).__name__)
        return user_id


async def fetch_comments_for_page(
    http: httpx.AsyncClient,
    token: str,
    page_id: str,
) -> list[dict]:
    """Fetch all comments for a page (handles pagination)."""
    all_comments: list[dict] = []
    start_cursor: str | None = None

    while True:
        params: dict[str, str] = {"block_id": page_id}
        if start_cursor:
            params["start_cursor"] = start_cursor

        try:
            resp = await http.get(
                f"{NOTION_API_BASE}/comments",
                headers=_notion_headers(token),
                params=params,
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("Failed to fetch comments for page %s: %s", page_id, type(exc).__name__)
            break

        all_comments.extend(parse_comments_response(data))

        if data.get("has_more") and data.get("next_cursor"):
            start_cursor = data["next_cursor"]
            await asyncio.sleep(REQUEST_DELAY)
        else:
            break

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
    """Query a Notion database for items assigned to the given user."""
    all_items: list[dict] = []
    start_cursor: str | None = None

    filter_body: dict = {
        "and": [
            {
                "property": assignee_property,
                "people": {"contains": user_id},
            },
            {
                "or": [
                    {"property": status_property, "status": {"equals": s}}
                    for s in open_statuses
                ]
            },
        ]
    }

    while True:
        body: dict = {"filter": filter_body}
        if start_cursor:
            body["start_cursor"] = start_cursor

        try:
            resp = await http.post(
                f"{NOTION_API_BASE}/databases/{database_id}/query",
                headers=_notion_headers(token),
                json=body,
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            logger.error(
                "Failed to query database %s: %s", database_id, type(exc).__name__
            )
            break

        title_property = "Name"  # default; callers rely on parse helper
        batch = parse_database_query_response(
            data,
            title_property=title_property,
            assignee_property=assignee_property,
            status_property=status_property,
        )
        all_items.extend(batch)

        if data.get("has_more") and data.get("next_cursor"):
            start_cursor = data["next_cursor"]
            await asyncio.sleep(REQUEST_DELAY)
        else:
            break

    return all_items


# ---------------------------------------------------------------------------
# Main scan entry point
# ---------------------------------------------------------------------------

async def scan_notion(
    config: ScannerConfig,
) -> tuple[list[TriageItem], dict[str, dict]]:
    """Scan Notion for assignments and @mentions.

    Returns (rule_based_items, mention_groups_for_classifier).
    """
    notion_cfg = config.notion
    if not notion_cfg.enabled or not notion_cfg.token or not notion_cfg.user_id:
        logger.info("Notion integration disabled or not configured -- skipping")
        return [], {}

    token = notion_cfg.token
    user_id = notion_cfg.user_id

    rule_based_items: list[TriageItem] = []
    mention_groups: dict[str, dict] = {}

    async with httpx.AsyncClient() as http:
        # 1. Scan monitored pages for @mention comments
        for page_id in notion_cfg.monitor_pages:
            await asyncio.sleep(REQUEST_DELAY)
            comments = await fetch_comments_for_page(http, token, page_id)
            mentioned = filter_mentions(comments, user_id)

            if not mentioned:
                continue

            page_title = await fetch_page_title(http, token, page_id)
            await asyncio.sleep(REQUEST_DELAY)

            # Resolve author names
            resolved_comments: list[dict] = []
            seen_user_ids: dict[str, str] = {}
            for comment in mentioned:
                author_id = comment["created_by_id"]
                if author_id not in seen_user_ids:
                    await asyncio.sleep(REQUEST_DELAY)
                    seen_user_ids[author_id] = await fetch_user_name(http, token, author_id)
                resolved_comments.append({
                    "created_by_name": seen_user_ids[author_id],
                    "text": comment["text"],
                    "created_time": comment["created_time"],
                })

            mention_groups[page_title] = {
                "page_id": page_id,
                "comments": resolved_comments,
            }

        # 2. Scan databases for assigned items
        for db_cfg in notion_cfg.databases:
            await asyncio.sleep(REQUEST_DELAY)
            assignments = await query_database_assignments(
                http,
                token,
                database_id=db_cfg.id,
                user_id=user_id,
                assignee_property=db_cfg.assignee_property,
                status_property=db_cfg.status_property,
                open_statuses=db_cfg.open_statuses,
            )
            rule_based_items.extend(assignments_to_triage_items(assignments))

    logger.info(
        "Notion scan complete: %d assignments, %d pages with mentions",
        len(rule_based_items),
        len(mention_groups),
    )
    return rule_based_items, mention_groups
