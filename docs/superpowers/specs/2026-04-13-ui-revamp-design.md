# Catch-up Dashboard UI Revamp -- Design Spec

**Date:** 2026-04-13
**Status:** Approved
**Scope:** Complete frontend redesign of the Next.js dashboard

## Overview

Replace the current 4-column Kanban board with a three-panel "Command Center" layout. The dashboard is used as a **safety net** -- the user handles most messages directly in Telegram/Notion but returns to the dashboard to catch what slipped through, or reactively when the bot escalates overdue items. The design optimizes for "what do I handle next?" answered in under 3 seconds.

## Visual Style: Navy/Slate

Blue-tinted dark theme inspired by Discord/Raycast. Warmer than pure black, easier on the eyes across different times of day.

### Color Tokens

```
Background:
  base:       #0c0f1a
  surface:    #141b33
  overlay:    #1a2340
  
Border:
  default:    #1e2a4a
  subtle:     #162038
  
Text:
  primary:    #e2e8f0
  secondary:  #64748b
  muted:      #475569
  
Accent:       #60a5fa
Accent dim:   #3b82f6

Priority:
  P0:         #f87171
  P1:         #fbbf24
  P2:         #4ade80
  P3:         #94a3b8

Source:
  telegram:   #2AABEE
  notion:     #7c3aed
  calendar:   #4ade80
  discord:    #5865F2
  github:     #e2e8f0
```

### Typography & Spacing

- Font: Inter (already in use)
- Border-radius: 10-12px cards/blocks, 50% avatars, 6px badges, 16px filter chips
- Hover states: subtle background lightening, no transform/shadow effects
- Transitions: 150ms ease for colors, backgrounds

## Layout: Three-Panel Command Center

```
+--------------------------------------------------+
|  Header: title / auto-refresh / analytics link   |
+----------+-------------------+-------------------+
|          |                   |                   |
|  Queue   |   Detail Pane    | Context Sidebar   |
|  300px   |   flex (1fr)     |   320px           |
|          |                   |                   |
|          |                   |                   |
+----------+-------------------+-------------------+
```

- Full viewport height (100vh minus header)
- Each panel scrolls independently
- Minimum center pane width: ~400px

### Responsive Breakpoints

- **>=1200px:** Three panels (full layout)
- **>=768px, <1200px:** Two panels (queue + detail). Context sidebar hidden, calendar/scanner info moves to a collapsible section at top of detail pane
- **<768px:** Single column (mobile). Queue is default view. Tapping an item pushes the detail view full-screen with a back button. All features available including reply. Bottom action bar for quick actions (Done / Snooze / Send draft)

## Panel 1: Focus Queue (Left, 300px)

### Header Section

```
+----------------------------------+
| Catch-up                    [R]  |
| 3 urgent, 5 this week           |
+----------------------------------+
| [To respond] [Done] [Snoozed] [F]|
+----------------------------------+
| [Search...]                      |
+----------------------------------+
```

- **Title:** "Catch-up" (h1, 16px, font-weight 600)
- **Summary line:** Natural language, dynamically generated: "3 urgent, 5 this week" or "All clear" or "1 overdue P0". Color-coded numbers (urgent in P0 color, etc.)
- **[R]:** Refresh button (auto-refresh keeps 30-min polling with visibility awareness)
- **Status tabs:** `To respond` (default) | `Done` | `Snoozed`. Active tab has accent underline. These are the `user_status` filter values: open/done/snoozed
- **[F]:** Filter icon button. Opens a popover with:
  - Source checkboxes: Telegram, Notion, Calendar, Discord, GitHub
  - Type checkboxes: DMs only, Groups only
  - Active filters shown as a small dot on the filter icon
- **Search:** Debounced text input (300ms), searches chat_name and preview

### Queue Items

Grouped by priority with section headers. P0/P1 sections expanded, P2/P3 collapsed by default.

**Section header:**
```
[dot] RESPOND TODAY                    3
```
- Priority dot (6px, priority color)
- Label in uppercase (10px, priority color, letter-spacing 0.5px)
- Count on the right (muted)
- Bottom border in priority color at 15% opacity
- P2/P3 headers are clickable to expand/collapse, show chevron

**Queue item:**
```
+----------------------------------+
| Matthew Graham        [TG]  2h  |
| Can you review the Phase II...  |
|                          3d wait |
+----------------------------------+
```

- **Name:** 12px, font-weight 600, primary text. Truncated with ellipsis
- **Source badge:** Inline after name. Pill-shaped (9px, 3px border-radius), translucent background with source color. One badge per item (each item has a single `source` field)
- **Time:** Right-aligned, 10px, muted text. Shows relative time ("2h", "1d", "3d")
- **Preview:** 11px, secondary text, single line, truncated
- **Waiting badge:** Right-aligned below time. Only shown when waiting_days >= 1. Red background for P0 items, amber for P1
- **Selected state:** Background changes to overlay color, left border 2px accent blue
- **Click:** Loads item in detail pane

### Queue Item Data Mapping

```
name         -> item.chat_name
source badge -> item.source (single value per item)
time         -> relative time from item.last_message_at
preview      -> item.preview (truncated to 1 line)
waiting      -> item.waiting_days (formatted as "<1d", "1d", "3d", etc.)
priority dot -> item.priority (in section header)
```

## Panel 2: Detail Pane (Center, flex)

### Empty State

When no item is selected, show centered content:
```
         [inbox icon]
    Select an item to view details
    
    3 urgent | 5 this week | 12 total
```

### Conversation Layout

When an item is selected:

**Header:**
```
+-----------------------------------------------+
| [MG]  Matthew Graham              [Snooze][Done]
|       DM -- 3d waiting  [TG] [P0]              |
+-----------------------------------------------+
```

- Avatar: 36px circle, initials (first letter of first+last word of chat_name), border in priority color (2px)
- Name: 14px, font-weight 600
- Meta line: chat_type ("DM" or "Group"), waiting time, source badge, priority badge
- Actions: Snooze button (ghost style), Done button (green)

**Their Message (left-aligned bubble):**
```
+----------------------------------+
| Can you review the Phase II      |
| proposal numbers before I submit?|
| The 5.5M figure needs...         |
+----------------------------------+
  2h ago
```

- Background: surface color, border 1px default border
- Border-radius: 10px 10px 10px 2px (square bottom-left = their side)
- Max-width: 85% of pane
- Text: 13px, primary color, line-height 1.6
- Timestamp below: 10px, muted

**AI Context (left-bordered note):**
```
| Phase II Extended Scope proposal. April 9 vote
| target. Matthew rarely asks for number reviews
| -- high-stakes validation request.
```

- Left border: 2px accent blue
- Padding: 8px 12px
- Text: 11px, secondary color
- Margin: 14px vertical

**Your Reply (right-aligned):**
```
                    +---------------------------+
                    | Hey Matthew -- just ran    |
                    | through the numbers...     |
                    +---------------------------+
               AI-drafted -- click to edit
```

When not editing:
- Background: accent at 8% opacity, border accent at 15%
- Border-radius: 2px 10px 10px 10px (square top-left = your side)
- Max-width: 85%, aligned right
- Italic text to indicate draft
- Click to switch to edit mode

When editing (after click or if no draft):
- Full-width textarea replaces the bubble
- Label: "Your Reply" (9px uppercase muted)
- Textarea: base background, default border, 10px border-radius, 13px text, min-height 80px
- Focus: border changes to accent

**Send Bar:**
```
+-----------------------------------------------+
| AI-drafted -- edit before sending   [Send via TG]
+-----------------------------------------------+
```

- Left: hint text (10px, muted)
- Right: "Send via Telegram" / "Send via Notion" etc. Primary button style (accent background, white text)
- For calendar items or items without chat_id: Send button hidden, only Done/Snooze available

**Sent confirmation:**
- Green subtle banner: "Reply queued -- will be sent within 2 minutes"
- Same pattern as current implementation (pending_replies table)

## Panel 3: Context Sidebar (Right, 320px)

All sections stacked vertically with 20px gap. Each section has an uppercase label header (11px, muted, letter-spacing 0.5px).

### 1. Overdue Alerts (conditional)

Only shown when P0 items >24h or P1 items >48h exist.

```
+----------------------------------+
| ! 2 items overdue                |
|   Matthew Graham (P0, 3d)       |
|   StraitsX (P0, 2d)             |
+----------------------------------+
```

- Background: P0 color at 8% opacity, border P0 at 20%
- Rounded 8px, padding 10px 12px
- Each item is a clickable link that selects it in the queue

### 2. Source Breakdown

```
SOURCES
TG ████████████ 12
NO ████         4
CA ██           2
```

- Horizontal mini bars, colored by source
- Count on the right
- Each bar clickable to filter queue by that source

### 3. Inbox Health (7 days)

```
INBOX HEALTH
[Mon][Tue][Wed][Thu][Fri][Sat][Sun]
```

- 7 small rectangles (flex, equal width, 24px height, 3px gap)
- Color intensity based on items cleared that day:
  - 0 cleared: P0 color at 15% opacity (red-ish)
  - 1-2 cleared: P1 color at 30%
  - 3-4 cleared: P2 color at 40%
  - 5+ cleared: P2 color at 60%
- Today has a border (1px default border) to distinguish
- Hover tooltip: "Mon: 5 cleared"
- Data source: count of items where user_status changed to "done", grouped by date, last 7 days

### 4. Today's Calendar

```
TODAY'S CALENDAR
+----------------------------------+
| 10:00  Mantle Weekly Sync       |
| 14:00  TokenLogic Standup       |
| 16:30  StraitsX Call            |
+----------------------------------+
```

- Each event: green left border (3px), overlay background, rounded 6px
- Time in source-calendar color, bold
- Title in primary text
- Data from existing calendar_scanner integration (items with source="calendar")

### 5. Scanner Status

```
SCANNER
[*] Last scan: 35m ago
    42/50 dialogs classified
    Next: 1:00 PM UTC
```

- Green pulsing dot (CSS animation)
- Text: 12px secondary color
- Data from latest scan record (scans table)

### 6. Mini Analytics

```
TREND (7D)
[sparkline chart]
  P0: 3  P1: 5  (click for full analytics)
```

- Tiny inline sparkline (40px height) showing P0+P1 open count over last 7 days
- Below: current P0/P1 counts
- Entire section is a link to `/analytics`
- Implementation: either a tiny canvas or SVG path, not Chart.js (too heavy for a sparkline)

### 7. Recent Activity

```
ACTIVITY
  9:41  Replied to Efe (PR review)
  9:12  Snoozed Lido V3 thread
  8:50  Marked Celo marketing done
```

- Last 5 actions from current day
- Time + description
- Data source: triage_items where user_status_at is today, ordered by recency

## Component Architecture

### New Components

```
dashboard/
  components/
    command-center/
      command-center.tsx        # Three-panel grid layout
      queue-panel.tsx           # Left panel container
      queue-header.tsx          # Title, summary, tabs, filter, search
      queue-section.tsx         # Priority group (header + items)
      queue-item.tsx            # Single queue item row
      detail-pane.tsx           # Center panel container
      detail-empty.tsx          # Empty state
      detail-conversation.tsx   # Conversation layout for selected item
      message-bubble.tsx        # Chat bubble (theirs or yours)
      reply-area.tsx            # Reply textarea + send button
      context-sidebar.tsx       # Right panel container
      overdue-alerts.tsx        # Conditional overdue section
      source-breakdown.tsx      # Source bar chart
      inbox-health.tsx          # 7-day heatmap
      calendar-events.tsx       # Today's calendar
      scanner-status.tsx        # Scan info
      mini-analytics.tsx        # Sparkline + link
      recent-activity.tsx       # Activity log
    ui/
      avatar.tsx                # Reusable avatar with priority ring
      source-badge.tsx          # Source pill badge
      waiting-badge.tsx         # Waiting time badge
      priority-dot.tsx          # Small colored dot
      filter-popover.tsx        # Filter dropdown
```

### Removed Components

```
kanban-board.tsx     -> replaced by command-center.tsx
kanban-column.tsx    -> replaced by queue-section.tsx
triage-card.tsx      -> replaced by queue-item.tsx
card-detail.tsx      -> replaced by detail-conversation.tsx
filter-bar.tsx       -> replaced by queue-header.tsx + filter-popover.tsx
stats-bar.tsx        -> replaced by queue-header.tsx + context-sidebar.tsx
search-input.tsx     -> integrated into queue-header.tsx
auto-refresh.tsx     -> integrated into queue-header.tsx
```

### Kept As-Is

```
analytics-chart.tsx  -> stays, used by /analytics page (theme colors updated)
```

### State Management

- **Selected item:** Client-side state in command-center.tsx, passed to detail pane
- **Filters:** URL search params (same as current: status, source, chatType, search)
- **Queue sections collapsed/expanded:** Client-side state, default P0/P1 open, P2/P3 closed
- **Reply editing:** Client-side state in reply-area.tsx
- **Auto-refresh:** Same 30-min interval with visibility awareness

### Data Flow

No backend changes needed. The existing data model and queries support everything:

- Queue items: `getTriageItems()` with filters, grouped client-side by priority
- Detail pane: selected item from the queue list (no additional fetch)
- Context sidebar:
  - Overdue: filtered from queue items (waiting_days > escalation thresholds)
  - Source breakdown: aggregated from queue items
  - Inbox health: new query -- count items by user_status_at date (last 7 days)
  - Calendar: filtered from queue items (source = "calendar")
  - Scanner: `getLatestScan()` (existing)
  - Mini analytics: `getAnalyticsData(7)` (existing)
  - Recent activity: new query -- items where user_status_at is today

### New Database Queries

Two new queries needed in `lib/db.ts`:

1. **getInboxHealthData(days: number):** Count of items marked done per day for the last N days
2. **getRecentActivity(limit: number):** Items where user_status changed today, ordered by user_status_at desc

## Pages

### `/` (Dashboard)

Server component that fetches scan + items, renders `<CommandCenter>`. Same `force-dynamic` behavior. Search params for filters.

### `/analytics`

Stays as-is. Update theme colors to navy/slate palette. Add a "Back to Dashboard" link.

### `/login`

Stays as-is. Update theme colors to match.

## Migration Strategy

This is a complete frontend replacement, not an incremental change:

1. Build all new components in `components/command-center/` and `components/ui/`
2. Update `globals.css` with new base colors
3. Replace `page.tsx` to render CommandCenter instead of StatsBar + FilterBar + KanbanBoard
4. Update `/analytics` and `/login` theme colors
5. Delete old components (kanban-board, kanban-column, triage-card, card-detail, filter-bar, stats-bar, search-input)
6. Keep auto-refresh logic, move into queue-header

## Out of Scope

- No backend/scanner changes
- No new data sources (Discord, GitHub remain future work)
- No database schema changes (existing tables sufficient)
- No authentication changes
- No new API routes
