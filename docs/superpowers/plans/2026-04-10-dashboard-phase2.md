# Dashboard Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Postgres database push to the scanner and build a Next.js Kanban dashboard on Vercel that displays triage items with filters, search, and mark-as-done.

**Architecture:** Scanner (Phase 1, already built) pushes scan results to Neon Postgres via `asyncpg`. Next.js App Router dashboard reads from the same database using `@neondatabase/serverless`. Kanban layout with 4 columns (P0-P3), dark theme, Server Components for data fetching, Server Actions for user interactions (mark done/snooze).

**Tech Stack:** Python `asyncpg` (scanner DB push), Next.js 15 App Router, Tailwind CSS, `@neondatabase/serverless`, Vercel deployment

**Spec:** `docs/specs/2026-04-10-catchup-dashboard-design.md`

**Existing code:** `scanner/` directory contains the working Python scanner (Phase 1). The dashboard is a new Next.js project in `dashboard/`.

---

## File Structure

```
catchup-dashboard/
  scanner/                          # Existing (Phase 1)
    src/
      database.py                   # NEW: asyncpg push to Postgres
    requirements.txt                # MODIFY: add asyncpg

  dashboard/                        # NEW: Next.js project
    app/
      layout.tsx                    # Root layout (dark theme, fonts)
      page.tsx                      # Main dashboard page (Server Component)
      actions.ts                    # Server Actions (mark done, snooze)
    components/
      kanban-board.tsx              # Kanban container (4 columns)
      kanban-column.tsx             # Single priority column
      triage-card.tsx               # Individual triage item card
      card-detail.tsx               # Expanded card with draft reply
      filter-bar.tsx                # Source/type/status filters
      stats-bar.tsx                 # Stats counters at top
      search-input.tsx              # Search box
    lib/
      db.ts                         # Neon Postgres client + queries
      types.ts                      # TypeScript types matching Python models
    tailwind.config.ts
    package.json
    tsconfig.json
    next.config.ts
    .env.local                      # DATABASE_URL (gitignored)

  schema.sql                        # Postgres schema (shared reference)
```

---

### Task 1: Postgres Schema + Scanner Database Push

**Files:**
- Create: `schema.sql`
- Create: `scanner/src/database.py`
- Modify: `scanner/requirements.txt`
- Modify: `scanner/src/scanner.py`
- Create: `scanner/tests/test_database.py`

- [ ] **Step 1: Create schema.sql at project root**

```sql
-- schema.sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE scans (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scanned_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  sources       TEXT[] NOT NULL,
  dialogs_listed     INT NOT NULL,
  dialogs_filtered   INT NOT NULL,
  dialogs_classified INT NOT NULL,
  stats         JSONB NOT NULL
);

CREATE TABLE triage_items (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scan_id         UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
  source          TEXT NOT NULL,
  chat_name       TEXT NOT NULL,
  chat_type       TEXT NOT NULL,
  waiting_person  TEXT,
  preview         TEXT NOT NULL,
  context_summary TEXT,
  draft_reply     TEXT,
  priority        TEXT NOT NULL,
  status          TEXT NOT NULL DEFAULT 'READ_NO_REPLY',
  tags            TEXT[] DEFAULT '{}',
  last_message_at  TIMESTAMPTZ,
  waiting_since    TIMESTAMPTZ,
  waiting_days     REAL,
  scanned_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  chat_id          BIGINT,
  message_id       BIGINT,
  user_status      TEXT DEFAULT 'open',
  user_status_at   TIMESTAMPTZ
);

CREATE INDEX idx_triage_scan ON triage_items(scan_id);
CREATE INDEX idx_triage_priority ON triage_items(priority);
CREATE INDEX idx_triage_user_status ON triage_items(user_status);
```

- [ ] **Step 2: Add asyncpg to requirements.txt**

Add to `scanner/requirements.txt`:
```
asyncpg>=0.29.0
```

Then install:
```bash
cd scanner && .venv/bin/pip install asyncpg
```

- [ ] **Step 3: Write failing test for database module**

```python
# scanner/tests/test_database.py
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from src.database import build_scan_insert, build_item_insert
from src.models import TriageItem, ScanResult, ScanStats, PriorityStats


def test_build_scan_insert():
    result = ScanResult(
        sources=["telegram"],
        dialogs_listed=80,
        dialogs_filtered=30,
        dialogs_classified=30,
        items=[],
        stats=ScanStats(
            total=0,
            by_priority=PriorityStats(P0=0, P1=0, P2=0, P3=0),
            by_status={},
        ),
    )
    query, params = build_scan_insert(result)
    assert "INSERT INTO scans" in query
    assert params[0] == ["telegram"]  # sources
    assert params[1] == 80  # dialogs_listed
    assert params[2] == 30  # dialogs_filtered
    assert params[3] == 30  # dialogs_classified
    stats_json = json.loads(params[4])
    assert stats_json["total"] == 0


def test_build_item_insert():
    item = TriageItem(
        source="telegram",
        chat_name="Logic Protocol Core",
        chat_type="group",
        waiting_person="Marc",
        preview="What about the vault params?",
        context_summary="Marc asking about vault params",
        draft_reply="Hey Marc, here are the params...",
        priority="P0",
        status="READ_NO_REPLY",
        tags=["deal blocker"],
        last_message_at=datetime(2026, 4, 7, 14, 0, tzinfo=timezone.utc),
        waiting_since=datetime(2026, 4, 7, 14, 0, tzinfo=timezone.utc),
        waiting_days=3,
        chat_id=-100123,
        message_id=42,
    )
    scan_id = "550e8400-e29b-41d4-a716-446655440000"
    query, params = build_item_insert(item, scan_id)
    assert "INSERT INTO triage_items" in query
    assert params[0] == scan_id
    assert params[1] == "telegram"
    assert params[2] == "Logic Protocol Core"
    assert params[4] == "Marc"
    assert params[8] == "P0"
    assert params[10] == ["deal blocker"]
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `cd scanner && .venv/bin/python -m pytest tests/test_database.py -v`
Expected: FAIL -- `ModuleNotFoundError`

- [ ] **Step 5: Implement database module**

```python
# scanner/src/database.py
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import asyncpg

from src.models import ScanResult, TriageItem

logger = logging.getLogger(__name__)


def build_scan_insert(result: ScanResult) -> tuple[str, list]:
    query = """
        INSERT INTO scans (sources, dialogs_listed, dialogs_filtered, dialogs_classified, stats, scanned_at)
        VALUES ($1, $2, $3, $4, $5::jsonb, $6)
        RETURNING id
    """
    stats_json = json.dumps(result.stats.model_dump())
    params = [
        result.sources,
        result.dialogs_listed,
        result.dialogs_filtered,
        result.dialogs_classified,
        stats_json,
        result.scanned_at,
    ]
    return query, params


def build_item_insert(item: TriageItem, scan_id: str) -> tuple[str, list]:
    query = """
        INSERT INTO triage_items (
            scan_id, source, chat_name, chat_type, waiting_person,
            preview, context_summary, draft_reply, priority, status,
            tags, last_message_at, waiting_since, waiting_days,
            chat_id, message_id, scanned_at
        ) VALUES (
            $1, $2, $3, $4, $5,
            $6, $7, $8, $9, $10,
            $11, $12, $13, $14,
            $15, $16, $17
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
        item.scanned_at if hasattr(item, "scanned_at") else datetime.now(timezone.utc),
    ]
    return query, params


async def push_to_database(database_url: str, result: ScanResult) -> str:
    conn = await asyncpg.connect(database_url)
    try:
        async with conn.transaction():
            # Insert scan record
            scan_query, scan_params = build_scan_insert(result)
            scan_id = await conn.fetchval(scan_query, *scan_params)

            # Insert all triage items
            for item in result.items:
                item_query, item_params = build_item_insert(item, str(scan_id))
                await conn.execute(item_query, *item_params)

            logger.info("Pushed scan %s with %d items to database", scan_id, len(result.items))
            return str(scan_id)
    finally:
        await conn.close()
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd scanner && .venv/bin/python -m pytest tests/test_database.py -v`
Expected: 2 tests PASS

- [ ] **Step 7: Wire database push into scanner.py**

Modify `scanner/src/scanner.py`. Read the file first, then add after the JSON output step (before the digest step):

Add import at top:
```python
from src.database import push_to_database
```

Add `database_url` to `OutputConfig` in `scanner/src/config.py`:
```python
class OutputConfig(BaseModel):
    telegram_digest: bool = True
    json_file: str = "scan_results.json"
    database_url: str | None = None
```

In `scanner.py`'s `run()` method, after the JSON write and before the digest, add:
```python
            # 8. Push to database
            if self._config.output.database_url:
                await push_to_database(self._config.output.database_url, result)
```

Add `database_url` to `config.yaml` under `output`:
```yaml
output:
  telegram_digest: true
  json_file: scan_results.json
  # database_url: set via DATABASE_URL env var
```

In `config.py`'s `from_yaml`, overlay DATABASE_URL:
```python
output_data = data.get("output", {})
db_url = os.environ.get("DATABASE_URL", "")
if db_url:
    output_data["database_url"] = db_url
data["output"] = output_data
```

- [ ] **Step 8: Run full test suite**

Run: `cd scanner && .venv/bin/python -m pytest tests/ -v`
Expected: all tests PASS (30 total)

- [ ] **Step 9: Commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add schema.sql scanner/src/database.py scanner/tests/test_database.py scanner/requirements.txt scanner/src/scanner.py scanner/src/config.py scanner/config.yaml
git commit -m "feat: database push -- asyncpg insert of scan results to Postgres"
```

---

### Task 2: Initialize Next.js Dashboard

**Files:**
- Create: `dashboard/` (via `create-next-app`)
- Create: `dashboard/lib/types.ts`
- Create: `dashboard/.env.local`

- [ ] **Step 1: Create Next.js project**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
npx create-next-app@latest dashboard --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*" --use-pnpm
```

When prompted: use defaults (App Router, Tailwind, ESLint, no Turbopack).

- [ ] **Step 2: Create shared types**

```typescript
// dashboard/lib/types.ts
export type Priority = "P0" | "P1" | "P2" | "P3";
export type Status = "NEW" | "READ_NO_REPLY" | "REPLIED" | "MONITORING";
export type UserStatus = "open" | "done" | "snoozed";
export type Source = "telegram" | "notion" | "github" | "calendar";
export type ChatType = "dm" | "group";

export interface TriageItem {
  id: string;
  scan_id: string;
  source: Source;
  chat_name: string;
  chat_type: ChatType;
  waiting_person: string | null;
  preview: string;
  context_summary: string | null;
  draft_reply: string | null;
  priority: Priority;
  status: Status;
  tags: string[];
  last_message_at: string | null;
  waiting_since: string | null;
  waiting_days: number | null;
  scanned_at: string;
  chat_id: number | null;
  message_id: number | null;
  user_status: UserStatus;
  user_status_at: string | null;
}

export interface ScanInfo {
  id: string;
  scanned_at: string;
  sources: string[];
  dialogs_listed: number;
  dialogs_filtered: number;
  dialogs_classified: number;
  stats: {
    total: number;
    by_priority: { P0: number; P1: number; P2: number; P3: number };
    by_status: Record<string, number>;
  };
}

export const PRIORITY_CONFIG: Record<Priority, { label: string; color: string; dotColor: string }> = {
  P0: { label: "Respond Today", color: "#f85149", dotColor: "bg-red-500" },
  P1: { label: "This Week", color: "#d29922", dotColor: "bg-amber-500" },
  P2: { label: "Respond", color: "#3fb950", dotColor: "bg-green-500" },
  P3: { label: "Monitor", color: "#8b949e", dotColor: "bg-gray-500" },
};

export const SOURCE_CONFIG: Record<Source, { label: string; color: string; bgColor: string }> = {
  telegram: { label: "TG", color: "#1f6feb", bgColor: "bg-blue-500/20 border-blue-500" },
  notion: { label: "Notion", color: "#7c3aed", bgColor: "bg-purple-500/20 border-purple-500" },
  github: { label: "GH", color: "#e6edf3", bgColor: "bg-gray-500/20 border-gray-500" },
  calendar: { label: "Cal", color: "#3fb950", bgColor: "bg-green-500/20 border-green-500" },
};
```

- [ ] **Step 3: Create .env.local**

```bash
echo "DATABASE_URL=postgresql://..." > dashboard/.env.local
```

Note: The actual DATABASE_URL will come from Neon setup. For now, use a placeholder. The engineer will need to provision a Neon database via Vercel Marketplace or directly at neon.tech and paste the connection string.

- [ ] **Step 4: Install Neon serverless driver**

```bash
cd dashboard && pnpm add @neondatabase/serverless
```

- [ ] **Step 5: Commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/ -f
git commit -m "feat: initialize Next.js dashboard with types and Neon driver"
```

---

### Task 3: Database Client + Queries

**Files:**
- Create: `dashboard/lib/db.ts`

- [ ] **Step 1: Create database client with queries**

```typescript
// dashboard/lib/db.ts
import { neon } from "@neondatabase/serverless";

function getDb() {
  const databaseUrl = process.env.DATABASE_URL;
  if (!databaseUrl) {
    throw new Error("DATABASE_URL is not set");
  }
  return neon(databaseUrl);
}

export async function getLatestScan(): Promise<{
  id: string;
  scanned_at: string;
  stats: { total: number; by_priority: { P0: number; P1: number; P2: number; P3: number }; by_status: Record<string, number> };
  dialogs_listed: number;
  dialogs_filtered: number;
  dialogs_classified: number;
} | null> {
  const sql = getDb();
  const rows = await sql`
    SELECT id, scanned_at, stats, dialogs_listed, dialogs_filtered, dialogs_classified
    FROM scans
    ORDER BY scanned_at DESC
    LIMIT 1
  `;
  if (rows.length === 0) return null;
  const row = rows[0];
  return {
    id: row.id,
    scanned_at: row.scanned_at,
    stats: typeof row.stats === "string" ? JSON.parse(row.stats) : row.stats,
    dialogs_listed: row.dialogs_listed,
    dialogs_filtered: row.dialogs_filtered,
    dialogs_classified: row.dialogs_classified,
  };
}

export async function getTriageItems(scanId: string, filters?: {
  userStatus?: string;
  source?: string;
  chatType?: string;
  search?: string;
}): Promise<import("./types").TriageItem[]> {
  const sql = getDb();

  const userStatus = filters?.userStatus ?? "open";

  const rows = await sql`
    SELECT *
    FROM triage_items
    WHERE scan_id = ${scanId}::uuid
      AND user_status = ${userStatus}
      AND (${filters?.source ?? ""} = '' OR source = ${filters?.source ?? ""})
      AND (${filters?.chatType ?? ""} = '' OR chat_type = ${filters?.chatType ?? ""})
      AND (
        ${filters?.search ?? ""} = ''
        OR chat_name ILIKE ${"%" + (filters?.search ?? "") + "%"}
        OR waiting_person ILIKE ${"%" + (filters?.search ?? "") + "%"}
        OR preview ILIKE ${"%" + (filters?.search ?? "") + "%"}
      )
    ORDER BY
      CASE priority
        WHEN 'P0' THEN 0
        WHEN 'P1' THEN 1
        WHEN 'P2' THEN 2
        WHEN 'P3' THEN 3
      END,
      waiting_days DESC NULLS LAST
  `;

  return rows as unknown as import("./types").TriageItem[];
}

export async function updateItemStatus(
  itemId: string,
  userStatus: "open" | "done" | "snoozed"
): Promise<void> {
  const sql = getDb();
  await sql`
    UPDATE triage_items
    SET user_status = ${userStatus}, user_status_at = now()
    WHERE id = ${itemId}::uuid
  `;
}
```

- [ ] **Step 2: Commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/lib/db.ts
git commit -m "feat: database client with scan queries and item status updates"
```

---

### Task 4: Dashboard Layout + Stats Bar

**Files:**
- Modify: `dashboard/app/layout.tsx`
- Modify: `dashboard/app/page.tsx`
- Create: `dashboard/components/stats-bar.tsx`

- [ ] **Step 1: Update root layout for dark theme**

```typescript
// dashboard/app/layout.tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Catch-up Dashboard",
  description: "Personal priority tracker across Telegram, Notion, GitHub",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-[#0d1117] text-[#e6edf3] min-h-screen`}>
        {children}
      </body>
    </html>
  );
}
```

- [ ] **Step 2: Update global CSS for dark theme**

Replace `dashboard/app/globals.css` with:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  background-color: #0d1117;
  color: #e6edf3;
}
```

- [ ] **Step 3: Create stats bar component**

```typescript
// dashboard/components/stats-bar.tsx
import { PRIORITY_CONFIG, type Priority } from "@/lib/types";

interface StatsBarProps {
  total: number;
  byPriority: Record<Priority, number>;
  scannedAt: string;
  dialogsListed: number;
  dialogsClassified: number;
}

export function StatsBar({ total, byPriority, scannedAt, dialogsListed, dialogsClassified }: StatsBarProps) {
  const scannedDate = new Date(scannedAt);
  const timeAgo = getTimeAgo(scannedDate);

  return (
    <div className="mb-6">
      <div className="flex items-baseline justify-between mb-4">
        <h1 className="text-xl font-bold">Catch-up Dashboard</h1>
        <span className="text-sm text-[#8b949e]">
          Last scan: {timeAgo} -- {dialogsClassified}/{dialogsListed} dialogs
        </span>
      </div>
      <div className="flex gap-3">
        <StatCard label="Total" value={total} color="#e6edf3" borderColor="#30363d" />
        {(["P0", "P1", "P2", "P3"] as const).map((p) => (
          <StatCard
            key={p}
            label={`${p} - ${PRIORITY_CONFIG[p].label}`}
            value={byPriority[p]}
            color={PRIORITY_CONFIG[p].color}
            borderColor={PRIORITY_CONFIG[p].color}
          />
        ))}
      </div>
    </div>
  );
}

function StatCard({ label, value, color, borderColor }: {
  label: string;
  value: number;
  color: string;
  borderColor: string;
}) {
  return (
    <div
      className="bg-[#161b22] rounded-lg px-5 py-3 text-center"
      style={{ borderWidth: 1, borderStyle: "solid", borderColor }}
    >
      <div className="text-2xl font-bold" style={{ color }}>{value}</div>
      <div className="text-xs text-[#8b949e]">{label}</div>
    </div>
  );
}

function getTimeAgo(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
```

- [ ] **Step 4: Create main page (Server Component)**

```typescript
// dashboard/app/page.tsx
import { getLatestScan, getTriageItems } from "@/lib/db";
import { StatsBar } from "@/components/stats-bar";
import { KanbanBoard } from "@/components/kanban-board";
import { FilterBar } from "@/components/filter-bar";
import type { Priority } from "@/lib/types";

export const dynamic = "force-dynamic";

interface PageProps {
  searchParams: Promise<{
    status?: string;
    source?: string;
    chatType?: string;
    search?: string;
  }>;
}

export default async function DashboardPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const scan = await getLatestScan();

  if (!scan) {
    return (
      <main className="max-w-7xl mx-auto px-6 py-8">
        <h1 className="text-xl font-bold mb-4">Catch-up Dashboard</h1>
        <p className="text-[#8b949e]">No scans yet. Run the scanner first:</p>
        <code className="block mt-2 bg-[#161b22] p-4 rounded-lg text-sm">
          cd scanner && python -m src.cli --config config.yaml --no-digest
        </code>
      </main>
    );
  }

  const items = await getTriageItems(scan.id, {
    userStatus: params.status ?? "open",
    source: params.source,
    chatType: params.chatType,
    search: params.search,
  });

  const byPriority: Record<Priority, typeof items> = {
    P0: items.filter((i) => i.priority === "P0"),
    P1: items.filter((i) => i.priority === "P1"),
    P2: items.filter((i) => i.priority === "P2"),
    P3: items.filter((i) => i.priority === "P3"),
  };

  return (
    <main className="max-w-7xl mx-auto px-6 py-8">
      <StatsBar
        total={scan.stats.total}
        byPriority={scan.stats.by_priority}
        scannedAt={scan.scanned_at}
        dialogsListed={scan.dialogs_listed}
        dialogsClassified={scan.dialogs_classified}
      />
      <FilterBar
        currentStatus={params.status ?? "open"}
        currentSource={params.source}
        currentChatType={params.chatType}
        currentSearch={params.search}
      />
      <KanbanBoard items={byPriority} />
    </main>
  );
}
```

- [ ] **Step 5: Commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/app/layout.tsx dashboard/app/globals.css dashboard/app/page.tsx dashboard/components/stats-bar.tsx
git commit -m "feat: dashboard layout, stats bar, and main page with data fetching"
```

---

### Task 5: Kanban Board + Triage Cards

**Files:**
- Create: `dashboard/components/kanban-board.tsx`
- Create: `dashboard/components/kanban-column.tsx`
- Create: `dashboard/components/triage-card.tsx`
- Create: `dashboard/components/card-detail.tsx`

- [ ] **Step 1: Create Kanban board container**

```typescript
// dashboard/components/kanban-board.tsx
import { KanbanColumn } from "./kanban-column";
import type { Priority, TriageItem } from "@/lib/types";

interface KanbanBoardProps {
  items: Record<Priority, TriageItem[]>;
}

export function KanbanBoard({ items }: KanbanBoardProps) {
  return (
    <div className="grid grid-cols-4 gap-4 mt-6">
      {(["P0", "P1", "P2", "P3"] as const).map((priority) => (
        <KanbanColumn key={priority} priority={priority} items={items[priority]} />
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Create Kanban column**

```typescript
// dashboard/components/kanban-column.tsx
import { PRIORITY_CONFIG, type Priority, type TriageItem } from "@/lib/types";
import { TriageCard } from "./triage-card";

interface KanbanColumnProps {
  priority: Priority;
  items: TriageItem[];
}

export function KanbanColumn({ priority, items }: KanbanColumnProps) {
  const config = PRIORITY_CONFIG[priority];

  return (
    <div className="flex flex-col">
      <div
        className="flex items-center gap-2 mb-3 pb-2"
        style={{ borderBottomWidth: 2, borderBottomStyle: "solid", borderBottomColor: config.color }}
      >
        <div className="w-2 h-2 rounded-full" style={{ backgroundColor: config.color }} />
        <span className="font-semibold text-sm">{priority} {config.label}</span>
        <span className="text-[#8b949e] text-xs">({items.length})</span>
      </div>
      <div className="flex flex-col gap-2">
        {items.map((item) => (
          <TriageCard key={item.id} item={item} />
        ))}
        {items.length === 0 && (
          <div className="text-[#8b949e] text-xs py-4 text-center">No items</div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create triage card**

```typescript
// dashboard/components/triage-card.tsx
"use client";

import { useState } from "react";
import { SOURCE_CONFIG, type TriageItem } from "@/lib/types";
import { CardDetail } from "./card-detail";

interface TriageCardProps {
  item: TriageItem;
}

export function TriageCard({ item }: TriageCardProps) {
  const [expanded, setExpanded] = useState(false);
  const sourceConfig = SOURCE_CONFIG[item.source];
  const waitText = item.waiting_days != null
    ? item.waiting_days < 1 ? "<1d" : `${Math.round(item.waiting_days)}d`
    : null;

  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-md p-3 text-xs">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left"
      >
        <div className="font-semibold text-[13px] mb-1 text-[#e6edf3]">
          {item.chat_name}
        </div>
        {item.waiting_person && (
          <div className="text-[#8b949e] mb-2">
            {item.waiting_person}{waitText ? ` -- ${waitText}` : ""}
          </div>
        )}
        <div className="flex gap-1 flex-wrap">
          <span
            className={`px-1.5 py-0.5 rounded text-[10px] border ${sourceConfig.bgColor}`}
          >
            {sourceConfig.label}
          </span>
          {item.chat_type === "dm" && (
            <span className="px-1.5 py-0.5 rounded text-[10px] border border-[#30363d] bg-[#30363d]/50">
              DM
            </span>
          )}
          {item.tags.slice(0, 2).map((tag) => (
            <span key={tag} className="px-1.5 py-0.5 rounded text-[10px] border border-[#30363d] text-[#8b949e]">
              {tag}
            </span>
          ))}
          {waitText && (
            <span className="px-1.5 py-0.5 rounded text-[10px] border border-[#30363d] text-[#d29922]">
              {waitText}
            </span>
          )}
        </div>
      </button>
      {expanded && <CardDetail item={item} />}
    </div>
  );
}
```

- [ ] **Step 4: Create card detail (expanded view)**

```typescript
// dashboard/components/card-detail.tsx
"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import type { TriageItem } from "@/lib/types";
import { markItemDone, snoozeItem } from "@/app/actions";

interface CardDetailProps {
  item: TriageItem;
}

export function CardDetail({ item }: CardDetailProps) {
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  function handleAction(action: (id: string) => Promise<void>) {
    startTransition(async () => {
      await action(item.id);
      router.refresh();
    });
  }

  return (
    <div className="mt-3 pt-3 border-t border-[#30363d]">
      {item.context_summary && (
        <p className="text-[#8b949e] text-xs mb-2">{item.context_summary}</p>
      )}
      {item.draft_reply && (
        <div className="bg-[#0d1117] rounded p-2 mb-3">
          <div className="text-[10px] text-[#8b949e] mb-1 uppercase tracking-wide">Draft reply</div>
          <p className="text-xs text-[#e6edf3]">{item.draft_reply}</p>
        </div>
      )}
      <div className="flex gap-2">
        <button
          onClick={() => handleAction(markItemDone)}
          disabled={isPending}
          className="px-2 py-1 text-[10px] rounded bg-[#238636] hover:bg-[#2ea043] text-white disabled:opacity-50"
        >
          {isPending ? "..." : "Done"}
        </button>
        <button
          onClick={() => handleAction(snoozeItem)}
          disabled={isPending}
          className="px-2 py-1 text-[10px] rounded bg-[#30363d] hover:bg-[#484f58] text-[#8b949e] disabled:opacity-50"
        >
          {isPending ? "..." : "Snooze"}
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/components/kanban-board.tsx dashboard/components/kanban-column.tsx dashboard/components/triage-card.tsx dashboard/components/card-detail.tsx
git commit -m "feat: kanban board with columns, triage cards, and expandable details"
```

---

### Task 6: Server Actions + Filter Bar

**Files:**
- Create: `dashboard/app/actions.ts`
- Create: `dashboard/components/filter-bar.tsx`
- Create: `dashboard/components/search-input.tsx`

- [ ] **Step 1: Create Server Actions**

```typescript
// dashboard/app/actions.ts
"use server";

import { updateItemStatus } from "@/lib/db";

export async function markItemDone(itemId: string): Promise<void> {
  await updateItemStatus(itemId, "done");
}

export async function snoozeItem(itemId: string): Promise<void> {
  await updateItemStatus(itemId, "snoozed");
}

export async function reopenItem(itemId: string): Promise<void> {
  await updateItemStatus(itemId, "open");
}
```

- [ ] **Step 2: Create filter bar**

```typescript
// dashboard/components/filter-bar.tsx
"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";
import { SearchInput } from "./search-input";

interface FilterBarProps {
  currentStatus?: string;
  currentSource?: string;
  currentChatType?: string;
  currentSearch?: string;
}

export function FilterBar({ currentStatus, currentSource, currentChatType, currentSearch }: FilterBarProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const setFilter = useCallback((key: string, value: string | undefined) => {
    const params = new URLSearchParams(searchParams.toString());
    if (value) {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    router.push(`?${params.toString()}`);
  }, [router, searchParams]);

  const statusFilters = [
    { value: "open", label: "To respond" },
    { value: "done", label: "Done" },
    { value: "snoozed", label: "Snoozed" },
  ];

  const sourceFilters = [
    { value: undefined, label: "All sources" },
    { value: "telegram", label: "Telegram" },
    { value: "notion", label: "Notion" },
    { value: "github", label: "GitHub" },
  ];

  const typeFilters = [
    { value: undefined, label: "All types" },
    { value: "dm", label: "DMs only" },
    { value: "group", label: "Groups only" },
  ];

  return (
    <div className="flex gap-2 flex-wrap items-center">
      {statusFilters.map((f) => (
        <FilterChip
          key={f.value}
          label={f.label}
          active={currentStatus === f.value}
          onClick={() => setFilter("status", f.value)}
        />
      ))}
      <div className="w-px h-5 bg-[#30363d] mx-1" />
      {sourceFilters.map((f) => (
        <FilterChip
          key={f.label}
          label={f.label}
          active={currentSource === f.value}
          onClick={() => setFilter("source", f.value)}
        />
      ))}
      <div className="w-px h-5 bg-[#30363d] mx-1" />
      {typeFilters.map((f) => (
        <FilterChip
          key={f.label}
          label={f.label}
          active={currentChatType === f.value}
          onClick={() => setFilter("chatType", f.value)}
        />
      ))}
      <div className="w-px h-5 bg-[#30363d] mx-1" />
      <SearchInput currentSearch={currentSearch} onSearch={(v) => setFilter("search", v || undefined)} />
    </div>
  );
}

function FilterChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1 rounded-full text-xs border transition-colors ${
        active
          ? "bg-[#388bfd22] border-[#388bfd] text-[#388bfd]"
          : "bg-[#161b22] border-[#30363d] text-[#8b949e] hover:text-[#e6edf3]"
      }`}
    >
      {label}
    </button>
  );
}
```

- [ ] **Step 3: Create search input**

```typescript
// dashboard/components/search-input.tsx
"use client";

import { useState, useEffect } from "react";

interface SearchInputProps {
  currentSearch?: string;
  onSearch: (value: string) => void;
}

export function SearchInput({ currentSearch, onSearch }: SearchInputProps) {
  const [value, setValue] = useState(currentSearch ?? "");

  useEffect(() => {
    const timeout = setTimeout(() => {
      if (value !== (currentSearch ?? "")) {
        onSearch(value);
      }
    }, 300);
    return () => clearTimeout(timeout);
  }, [value, currentSearch, onSearch]);

  return (
    <input
      type="text"
      placeholder="Search..."
      value={value}
      onChange={(e) => setValue(e.target.value)}
      className="bg-[#161b22] border border-[#30363d] rounded-full px-3 py-1 text-xs text-[#e6edf3] placeholder-[#8b949e] outline-none focus:border-[#388bfd] w-48"
    />
  );
}
```

- [ ] **Step 4: Verify build**

```bash
cd dashboard && pnpm build
```

Expected: Build succeeds (may show warnings about missing DATABASE_URL at build time, which is expected since it's a dynamic page).

- [ ] **Step 5: Commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/app/actions.ts dashboard/components/filter-bar.tsx dashboard/components/search-input.tsx
git commit -m "feat: server actions for done/snooze and filter bar with search"
```

---

### Task 7: Provision Database + End-to-End Test

**Files:**
- Modify: `scanner/.env` (add DATABASE_URL)
- Modify: `dashboard/.env.local` (add DATABASE_URL)

This task provisions the Neon database, runs the schema, pushes scan data, and verifies the dashboard reads it.

- [ ] **Step 1: Provision Neon Postgres**

Option A (Vercel Marketplace):
```bash
cd dashboard && vercel link
vercel integration add neon
```

Option B (neon.tech directly):
1. Go to https://neon.tech
2. Create a new project "catchup-dashboard"
3. Copy the connection string

- [ ] **Step 2: Run schema migration**

```bash
psql "$DATABASE_URL" -f /Users/akgemilio/Projects/catchup-dashboard/schema.sql
```

Or via Neon SQL Editor: paste the contents of `schema.sql`.

- [ ] **Step 3: Set DATABASE_URL in scanner .env**

Add to `scanner/.env`:
```
DATABASE_URL=postgresql://neondb_owner:...@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
```

- [ ] **Step 4: Run scanner with database push**

```bash
cd scanner && .venv/bin/python -m src.cli --config config.yaml --no-digest
```

Expected: Scanner runs, classifies, and logs "Pushed scan ... with N items to database".

- [ ] **Step 5: Verify data in database**

```bash
psql "$DATABASE_URL" -c "SELECT id, scanned_at, (stats->>'total')::int as total FROM scans ORDER BY scanned_at DESC LIMIT 1;"
psql "$DATABASE_URL" -c "SELECT priority, count(*) FROM triage_items GROUP BY priority ORDER BY priority;"
```

Expected: One scan row, items grouped by P0/P1/P2/P3.

- [ ] **Step 6: Set DATABASE_URL in dashboard .env.local**

```bash
echo "DATABASE_URL=postgresql://neondb_owner:...@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require" > dashboard/.env.local
```

- [ ] **Step 7: Start dashboard dev server**

```bash
cd dashboard && pnpm dev
```

Open http://localhost:3000. Expected: Kanban board with 4 columns showing triage items from the scan.

- [ ] **Step 8: Test interactions**

1. Click a card to expand it -- verify context summary and draft reply show
2. Click "Done" on a card -- verify it disappears from the board
3. Switch filter to "Done" -- verify the dismissed card appears there
4. Use search -- verify filtering works

- [ ] **Step 9: Commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add schema.sql scanner/config.yaml
git commit -m "feat: end-to-end database integration verified"
```

---

### Task 8: Deploy to Vercel

**Files:**
- Create: `dashboard/vercel.json` (if needed)

- [ ] **Step 1: Link project to Vercel**

```bash
cd dashboard && vercel link
```

- [ ] **Step 2: Set environment variable**

```bash
vercel env add DATABASE_URL production
```

Paste the Neon connection string when prompted.

- [ ] **Step 3: Deploy**

```bash
vercel --prod
```

- [ ] **Step 4: Verify production deployment**

Open the deployment URL. Verify the Kanban board loads with data.

- [ ] **Step 5: Commit deployment config**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/
git commit -m "feat: Vercel deployment configuration"
```

---

## Summary

8 tasks. After completion:

1. Scanner pushes results to Neon Postgres (`DATABASE_URL` in `.env`)
2. Next.js Kanban dashboard reads from the same database
3. Dashboard deployed on Vercel, accessible from phone/desktop
4. Mark done / snooze / filter / search all work
5. Dark theme matching the mockup

**Workflow after Phase 2:**
```bash
# Run scanner (locally or on cron)
cd scanner && python -m src.cli --config config.yaml

# View dashboard
open https://your-app.vercel.app
```
