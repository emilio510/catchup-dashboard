from __future__ import annotations

import logging
import os
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
    skip_words = {"call", "meeting", "sync", "review", "weekly", "daily", "the", "and", "with", "for", "prep", "new"}
    for event in events:
        for word in event.summary.split():
            cleaned = word.strip("()[],-:").lower()
            if len(cleaned) >= 3 and cleaned not in skip_words:
                keywords.add(cleaned)

    related = []
    for name in chat_names:
        name_lower = name.lower()
        if any(kw in name_lower for kw in keywords):
            related.append(name)
    return related


def _get_credentials(credentials_path: Path, token_path: Path) -> Credentials:
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not credentials_path.exists():
                raise FileNotFoundError(
                    f"Google credentials not found at {credentials_path}. "
                    "Download from Google Cloud Console > APIs & Services > Credentials > OAuth 2.0 Client IDs"
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)

        token_path.write_text(creds.to_json())

    return creds


async def fetch_calendar_events(
    credentials_path: Path,
    token_path: Path,
    days_ahead: int = 7,
) -> list[CalendarEvent]:
    creds = _get_credentials(credentials_path, token_path)
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
            start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            end = datetime.fromisoformat(end_str.replace("Z", "+00:00")) if end_str else start + timedelta(hours=1)
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
