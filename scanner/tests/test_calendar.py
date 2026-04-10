from datetime import datetime, timezone, timedelta
from src.calendar_scanner import CalendarEvent, format_events_for_classifier, find_related_chat_names


def test_calendar_event_creation():
    event = CalendarEvent(
        summary="Mantle Incentives Weekly Call",
        start=datetime(2026, 4, 11, 15, 0, tzinfo=timezone.utc),
        end=datetime(2026, 4, 11, 16, 0, tzinfo=timezone.utc),
        location="Google Meet",
        description="Weekly sync on MNT incentive program",
        attendees=["alice@mantle.xyz"],
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


def test_find_related_chat_names():
    events = [
        CalendarEvent(summary="Mantle Incentives Weekly", start=datetime.now(timezone.utc), end=datetime.now(timezone.utc)),
        CalendarEvent(summary="StraitsX x Grab Deal Review", start=datetime.now(timezone.utc), end=datetime.now(timezone.utc)),
        CalendarEvent(summary="Dentist Appointment", start=datetime.now(timezone.utc), end=datetime.now(timezone.utc)),
    ]
    chat_names = ["Mantle <> Aave", "Aave & OKX co-pitch - StraitsX & Grab", "TokenLogic Core", "DeFi Gs"]
    related = find_related_chat_names(events, chat_names)
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
