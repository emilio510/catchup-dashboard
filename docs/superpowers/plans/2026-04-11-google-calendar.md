# Google Calendar Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fetch upcoming Google Calendar events and use them to boost priority of related Telegram conversations + create standalone "meeting prep" triage items.

**Architecture:** A new `calendar_scanner.py` module uses the Google Calendar API (`google-api-python-client`) to fetch events in the next 7 days. Events are passed to the classifier as extra context alongside Telegram conversations. Events that have related Telegram chats get their priority boosted. Events with no related chat create standalone triage items with source="calendar". OAuth2 credentials are stored locally (one-time browser auth flow).

**Tech Stack:** `google-api-python-client`, `google-auth-oauthlib` (OAuth2 flow), `google-auth-httplib2`

---

## File Structure

```
scanner/
  src/
    calendar_scanner.py    # CREATE: fetch events, format for classifier
  tests/
    test_calendar.py       # CREATE: tests for event formatting
  credentials.json         # User provides (from Google Cloud Console)
  token.json               # Auto-generated after first OAuth flow (gitignored)
  config.yaml              # MODIFY: add calendar section
  requirements.txt         # MODIFY: add google packages
  src/
    scanner.py             # MODIFY: wire calendar into pipeline
    classifier.py          # MODIFY: accept calendar events in prompt
    config.py              # MODIFY: add calendar config
```

---

### Task 1: Google Calendar Module

**Files:**
- Create: `scanner/src/calendar_scanner.py`
- Create: `scanner/tests/test_calendar.py`
- Modify: `scanner/requirements.txt`

- [ ] **Step 1: Add Google dependencies to requirements.txt**

Append to `scanner/requirements.txt`:
```
google-api-python-client>=2.0.0
google-auth-oauthlib>=1.0.0
google-auth-httplib2>=0.2.0
```

Install:
```bash
cd scanner && .venv/bin/pip install google-api-python-client google-auth-oauthlib google-auth-httplib2
```

- [ ] **Step 2: Write failing tests for calendar event formatting**

```python
# scanner/tests/test_calendar.py
from datetime import datetime, timezone, timedelta
from src.calendar_scanner import CalendarEvent, format_events_for_classifier, find_related_chat_names


def test_calendar_event_creation():
    event = CalendarEvent(
        summary="Mantle Incentives Weekly Call",
        start=datetime(2026, 4, 11, 15, 0, tzinfo=timezone.utc),
        end=datetime(2026, 4, 11, 16, 0, tzinfo=timezone.utc),
        location="Google Meet",
        description="Weekly sync on MNT incentive program",
        attendees=["alice@mantle.xyz", "emile@tokenlogic.xyz"],
    )
    assert event.summary == "Mantle Incentives Weekly Call"
    assert event.days_until(datetime(2026, 4, 10, 10, 0, tzinfo=timezone.utc)) == 1


def test_calendar_event_days_until_today():
    now = datetime.now(timezone.utc)
    event = CalendarEvent(
        summary="Test",
        start=now + timedelta(hours=3),
        end=now + timedelta(hours=4),
    )
    assert event.days_until(now) == 0


def test_format_events_for_classifier():
    events = [
        CalendarEvent(
            summary="Mantle Call",
            start=datetime(2026, 4, 11, 15, 0, tzinfo=timezone.utc),
            end=datetime(2026, 4, 11, 16, 0, tzinfo=timezone.utc),
            description="Weekly sync",
        ),
        CalendarEvent(
            summary="StraitsX x Grab Review",
            start=datetime(2026, 4, 12, 10, 0, tzinfo=timezone.utc),
            end=datetime(2026, 4, 12, 11, 0, tzinfo=timezone.utc),
        ),
    ]
    text = format_events_for_classifier(events)
    assert "Mantle Call" in text
    assert "StraitsX" in text
    assert "Apr 11" in text or "2026-04-11" in text


def test_find_related_chat_names():
    events = [
        CalendarEvent(summary="Mantle Incentives Weekly", start=datetime.now(timezone.utc), end=datetime.now(timezone.utc)),
        CalendarEvent(summary="StraitsX x Grab Deal Review", start=datetime.now(timezone.utc), end=datetime.now(timezone.utc)),
        CalendarEvent(summary="Dentist Appointment", start=datetime.now(timezone.utc), end=datetime.now(timezone.utc)),
    ]
    chat_names = ["Mantle <> Aave", "Aave & OKX co-pitch - StraitsX & Grab", "TokenLogic Core", "DeFi Gs"]
    related = find_related_chat_names(events, chat_names)
    # "Mantle" matches "Mantle <> Aave", "StraitsX" or "Grab" matches the co-pitch chat
    assert "Mantle <> Aave" in related
    assert "Aave & OKX co-pitch - StraitsX & Grab" in related
    assert "DeFi Gs" not in related


def test_find_related_no_matches():
    events = [
        CalendarEvent(summary="Dentist", start=datetime.now(timezone.utc), end=datetime.now(timezone.utc)),
    ]
    chat_names = ["TokenLogic Core"]
    related = find_related_chat_names(events, chat_names)
    assert len(related) == 0
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd scanner && .venv/bin/python -m pytest tests/test_calendar.py -v`

- [ ] **Step 4: Implement calendar module**

```python
# scanner/src/calendar_scanner.py
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
    skip_words = {"call", "meeting", "sync", "review", "weekly", "daily", "the", "and", "with", "for", "prep"}
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd scanner && .venv/bin/python -m pytest tests/test_calendar.py -v`
Expected: 5 tests PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add scanner/requirements.txt scanner/src/calendar_scanner.py scanner/tests/test_calendar.py
git commit -m "feat: Google Calendar module -- fetch events, format for classifier, find related chats"
```

---

### Task 2: Wire Calendar into Scanner + Classifier

**Files:**
- Modify: `scanner/src/config.py`
- Modify: `scanner/src/classifier.py`
- Modify: `scanner/src/scanner.py`
- Modify: `scanner/config.yaml`
- Modify: `scanner/.gitignore` (or project root `.gitignore`)

- [ ] **Step 1: Add calendar config**

In `scanner/src/config.py`, add a new config section after `OutputConfig`:

```python
class CalendarConfig(BaseModel):
    enabled: bool = False
    credentials_path: str = "credentials.json"
    token_path: str = "token.json"
    days_ahead: int = 7
```

Add it to `ScannerConfig`:

```python
class ScannerConfig(BaseModel):
    scan: ScanConfig = Field(default_factory=ScanConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    classification: ClassificationConfig = Field(default_factory=ClassificationConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    calendar: CalendarConfig = Field(default_factory=CalendarConfig)
```

- [ ] **Step 2: Update classifier to accept calendar context**

In `scanner/src/classifier.py`, modify `build_classification_prompt` to accept an optional calendar context string:

```python
def build_classification_prompt(
    conversations: list[ConversationData],
    my_display_name: str,
    user_context: str,
    calendar_context: str = "",
) -> str:
    parts = [
        f"User context: {user_context}",
        f"User's display name in chats: {my_display_name}",
        f"Current time: {datetime.now(timezone.utc).isoformat()}",
        "",
    ]

    if calendar_context:
        parts.append(calendar_context)
        parts.append("")
        parts.append("IMPORTANT: If a conversation is related to an upcoming calendar event, boost its priority. Meeting prep should be at least P1.")
        parts.append("")

    parts.append("Conversations to classify:")
    parts.append("")

    for conv in conversations:
        parts.append(f"--- CHAT: {conv.dialog.name} (type: {conv.chat_type}) ---")
        for msg in conv.messages:
            parts.append(msg.format())
        parts.append("")

    return "\n".join(parts)
```

Update the call in `classify_batch` to pass `calendar_context`:

In the `Classifier` class, add `calendar_context` as an instance variable:

```python
class Classifier:
    def __init__(self, config: ScannerConfig) -> None:
        self._config = config
        self._client = anthropic.AsyncAnthropic(api_key=config.classification.api_key)
        self.calendar_context: str = ""
```

Then in `classify_batch`, pass it:

```python
        prompt = build_classification_prompt(
            conversations,
            my_display_name,
            self._config.classification.user_context,
            calendar_context=self.calendar_context,
        )
```

- [ ] **Step 3: Wire calendar into scanner.py**

In `scanner/src/scanner.py`, add the calendar fetch between the Telegram read step and the classify step.

Add import at top:
```python
from src.calendar_scanner import fetch_calendar_events, format_events_for_classifier, find_related_chat_names, CalendarEvent
```

In the `run()` method, after the dedup block and before classification, add:

```python
            # 3b. Fetch calendar events (if enabled)
            calendar_events: list[CalendarEvent] = []
            if self._config.calendar.enabled:
                try:
                    from pathlib import Path
                    calendar_events = await fetch_calendar_events(
                        credentials_path=Path(self._config.calendar.credentials_path),
                        token_path=Path(self._config.calendar.token_path),
                        days_ahead=self._config.calendar.days_ahead,
                    )
                    self._classifier.calendar_context = format_events_for_classifier(calendar_events)

                    # Find chats related to upcoming events and ensure they're in the classify list
                    if calendar_events and conversations:
                        all_chat_names = [c.dialog.name for c in conversations]
                        related = find_related_chat_names(calendar_events, all_chat_names)
                        if related:
                            logger.info("Calendar: %d chats related to upcoming events: %s", len(related), related)
                except Exception:
                    logger.exception("Failed to fetch calendar events (continuing without)")
```

Also update the `sources` list in the ScanResult to include "calendar" when events were fetched:

```python
            sources = ["telegram"]
            if calendar_events:
                sources.append("calendar")
```

- [ ] **Step 4: Update config.yaml**

Add to `scanner/config.yaml`:

```yaml
calendar:
  enabled: false  # Set to true after OAuth setup
  credentials_path: credentials.json
  token_path: token.json
  days_ahead: 7
```

- [ ] **Step 5: Add token.json and credentials.json to gitignore**

Append to project root `.gitignore`:
```
scanner/token.json
scanner/credentials.json
```

- [ ] **Step 6: Run full test suite**

Run: `cd scanner && .venv/bin/python -m pytest tests/ -v`
Expected: all tests pass. The `build_classification_prompt` tests in `test_classifier.py` should still pass since `calendar_context` defaults to `""`.

- [ ] **Step 7: Commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add scanner/src/config.py scanner/src/classifier.py scanner/src/scanner.py scanner/config.yaml .gitignore
git commit -m "feat: wire Google Calendar into scanner pipeline -- events boost related chat priority"
```

---

### Task 3: Google OAuth Setup + Smoke Test

This task requires user interaction (browser OAuth flow).

- [ ] **Step 1: Create Google Cloud credentials**

1. Go to https://console.cloud.google.com
2. Create a project (or use an existing one)
3. Enable "Google Calendar API" (APIs & Services > Enable APIs)
4. Go to APIs & Services > Credentials
5. Create OAuth 2.0 Client ID (type: Desktop App)
6. Download the JSON and save as `scanner/credentials.json`

- [ ] **Step 2: Run the OAuth flow**

```bash
cd scanner && .venv/bin/python3 -c "
from src.calendar_scanner import _get_credentials
from pathlib import Path
creds = _get_credentials(Path('credentials.json'), Path('token.json'))
print('Auth successful! Token saved to token.json')
"
```

This opens a browser window for Google OAuth consent. After granting access, `token.json` is saved locally.

- [ ] **Step 3: Enable calendar in config.yaml**

Change `enabled: false` to `enabled: true` in config.yaml:

```yaml
calendar:
  enabled: true
```

- [ ] **Step 4: Run scanner with calendar**

```bash
cd scanner && .venv/bin/python -m src.cli --config config.yaml --no-digest -v
```

Expected output should include:
- "Fetched N calendar events for next 7 days"
- "Calendar: X chats related to upcoming events: [...]"
- Classification results that reference calendar events

- [ ] **Step 5: Commit config change**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add scanner/config.yaml
git commit -m "feat: enable Google Calendar integration"
git push
```

---

## Summary

3 tasks:
1. **Calendar module** -- fetch events, format for classifier, find related chats (pure Python, fully testable)
2. **Wire into scanner** -- config, classifier prompt, scanner pipeline (integration)
3. **OAuth setup + smoke test** -- requires user interaction for Google auth

After completion: the scanner fetches your next 7 days of calendar events and uses them to:
- Boost priority of Telegram chats related to upcoming meetings
- Give the classifier context like "Mantle call tomorrow" so it marks Mantle-related chats as P1+
- The classifier prompt includes: "If a conversation is related to an upcoming calendar event, boost its priority"
