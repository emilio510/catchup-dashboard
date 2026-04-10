from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


Source = Literal["telegram", "notion", "github", "calendar"]
Priority = Literal["P0", "P1", "P2", "P3"]
Status = Literal["NEW", "READ_NO_REPLY", "REPLIED", "MONITORING"]
ChatType = Literal["dm", "group"]
UserStatus = Literal["open", "done", "snoozed"]


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


class PriorityStats(BaseModel):
    P0: int = 0
    P1: int = 0
    P2: int = 0
    P3: int = 0


class ScanStats(BaseModel):
    total: int
    by_priority: PriorityStats
    by_status: dict[str, int] = Field(default_factory=dict)


class ScanResult(BaseModel):
    scanned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sources: list[str]
    dialogs_listed: int
    dialogs_filtered: int
    dialogs_classified: int
    items: list[TriageItem]
    stats: ScanStats
