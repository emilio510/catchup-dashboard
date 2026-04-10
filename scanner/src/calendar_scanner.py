from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


@dataclass(frozen=True)
class CalendarEvent:
    summary: str
    start: datetime
    end: datetime
    location: str | None = None
    description: str | None = None
    attendees: list[str] = field(default_factory=list)

    def days_until(self, now: datetime) -> int:
        delta = self.start - now
        return max(0, int(delta.total_seconds() // 86400))

    def format_short(self) -> str:
        day = self.start.strftime("%b %d")
        time = self.start.strftime("%H:%M")
        days = self.days_until(datetime.now(timezone.utc))
        when = "today" if days == 0 else f"in {days}d" if days <= 7 else day
        return f"{self.summary} -- {day} {time} UTC ({when})"


def format_events_for_classifier(events: list[CalendarEvent]) -> str:
    if not events:
        return ""
    lines = ["Upcoming calendar events (next 7 days):"]
    for event in events:
        lines.append(f"  - {event.format_short()}")
        if event.description:
            lines.append(f"    Description: {event.description[:200]}")
    return "\n".join(lines)


def find_related_chat_names(
    events: list[CalendarEvent], chat_names: list[str]
) -> list[str]:
    keywords: set[str] = set()
    skip_words = {
        "call", "meeting", "sync", "review", "weekly", "daily",
        "the", "and", "with", "for", "prep", "new",
        "aave", "token", "logic", "tokenlogic", "defi", "dao",
        "protocol", "standup", "service", "planning", "demo",
        "day", "catchup", "projects",
    }
    for event in events:
        for word in event.summary.split():
            cleaned = word.strip("()[],-:").lower()
            if len(cleaned) >= 3 and cleaned not in skip_words:
                keywords.add(cleaned)

    related = []
    for name in chat_names:
        name_lower = name.lower()
        if any(re.search(rf'\b{re.escape(kw)}\b', name_lower) for kw in keywords):
            related.append(name)
    return related


def events_to_triage_items(events: list[CalendarEvent]) -> list:
    """Convert calendar events into TriageItem-compatible dicts for the dashboard."""
    from src.models import TriageItem

    now = datetime.now(timezone.utc)
    items = []
    seen_summaries: set[str] = set()

    for event in events:
        # Skip duplicates (same event appearing twice)
        if event.summary in seen_summaries:
            continue
        seen_summaries.add(event.summary)

        days = event.days_until(now)

        # Priority based on how soon the event is
        if days == 0:
            priority = "P0"
        elif days <= 2:
            priority = "P1"
        elif days <= 5:
            priority = "P2"
        else:
            priority = "P3"

        tags = ["calendar"]
        if days == 0:
            tags.append("today")
        elif days == 1:
            tags.append("tomorrow")

        day_str = event.start.strftime("%b %d")
        time_str = event.start.strftime("%H:%M UTC")
        when = "today" if days == 0 else "tomorrow" if days == 1 else f"in {days} days"

        attendees_str = ""
        if event.attendees:
            attendees_str = f" with {', '.join(a.split('@')[0] for a in event.attendees[:3])}"

        items.append(TriageItem(
            source="calendar",
            chat_name=event.summary,
            chat_type="group",
            waiting_person=None,
            preview=f"{day_str} at {time_str} ({when}){attendees_str}",
            context_summary=event.description[:200] if event.description else f"Upcoming event {when}",
            draft_reply=None,
            priority=priority,
            status="NEW",
            tags=tags,
            last_message_at=event.start,
            waiting_since=None,
            waiting_days=None,
            chat_id=None,
            message_id=None,
        ))

    return items


def _get_credentials(credentials_path: Path, token_path: Path) -> Credentials | None:
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not credentials_path.exists():
                logger.warning(
                    "Google credentials not found at %s. Calendar integration disabled. "
                    "See README for setup instructions.",
                    credentials_path,
                )
                return None
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)

        token_path.write_text(creds.to_json())

    return creds


def _fetch_calendar_events_sync(
    credentials_path: Path,
    token_path: Path,
    days_ahead: int,
) -> list[CalendarEvent]:
    creds = _get_credentials(credentials_path, token_path)
    if creds is None:
        return []

    service = build("calendar", "v3", credentials=creds)

    now = datetime.now(timezone.utc)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=days_ahead)).isoformat()

    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            maxResults=50,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    events = []
    for item in events_result.get("items", []):
        start_raw = item.get("start", {})
        end_raw = item.get("end", {})

        start_str = start_raw.get("dateTime") or start_raw.get("date")
        end_str = end_raw.get("dateTime") or end_raw.get("date")

        if not start_str:
            continue

        try:
            if "T" not in start_str:
                start = datetime.fromisoformat(start_str).replace(tzinfo=timezone.utc)
            else:
                start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))

            if end_str:
                if "T" not in end_str:
                    end = datetime.fromisoformat(end_str).replace(tzinfo=timezone.utc)
                else:
                    end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
            else:
                end = start + timedelta(hours=1)
        except (ValueError, TypeError):
            continue

        attendees = [
            a.get("email", "")
            for a in item.get("attendees", [])
            if a.get("email")
        ]

        events.append(
            CalendarEvent(
                summary=item.get("summary", "Untitled"),
                start=start,
                end=end,
                location=item.get("location"),
                description=item.get("description"),
                attendees=attendees,
            )
        )

    logger.info("Fetched %d calendar events for next %d days", len(events), days_ahead)
    return events


async def fetch_calendar_events(
    credentials_path: Path,
    token_path: Path,
    days_ahead: int = 7,
) -> list[CalendarEvent]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, _fetch_calendar_events_sync, credentials_path, token_path, days_ahead
    )
