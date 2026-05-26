# Catchup Dashboard — Monochrome Glass Redesign

**Date:** 2026-05-26
**Status:** Approved design, ready for implementation plan
**Scope:** Pure cosmetic refactor + inline-style → Tailwind migration. No data, no scanner, no API changes. No tests added (no test infra exists yet).

## Summary

Apply the monochrome-glass house system (per `~/Projects/ethena-flow-monitor/docs/superpowers/specs/2026-05-25-monochrome-glass-redesign-design.md`) to the Catchup Dashboard. The 3-pane Command Center layout (Queue | Detail | Sidebar) stays — every component inside it gets re-skinned. As a prep step on the same branch, inline `style={{...}}` objects across all 17 command-center components migrate to Tailwind utility classes so the token system has something to bind to.

The dashboard's signal-driven structure is already a perfect match for the house system: P0/P1/P2/P3 priorities map directly onto the `risk`/`warn`/`ok`/`ghost` semantic tones, and the existing escalation logic (P0 > 24h, P1 > 48h) gives the HeroMeter a natural target.

## Goals

1. Visual parity with Ethena Flow Monitor — same tokens, same primitives, same motion vocabulary
2. Preserve the 3-pane Command Center layout and every existing data point
3. Surface the most urgent signal (overdue P0/P1 count) in the Queue panel header where work begins
4. Move every component off inline styles to Tailwind utility classes — without this, the token system can't apply uniformly
5. Respect `prefers-reduced-motion`

## Non-goals

- Scanner / Python code changes
- Database schema changes
- API or routing changes
- Adding/removing data points or widgets
- Mobile rebuild (the existing breakpoint logic in `command-center.tsx` is fine — just gets restyled)

## Design system

The full token block, glass utility, motion keyframes, primitives, and "what NOT to do" list live in:
`~/Projects/ethena-flow-monitor/docs/superpowers/specs/2026-05-25-monochrome-glass-redesign-design.md`

The catchup dashboard imports this system wholesale. The catchup port uses **4 of the 6** primitives — `GlassCard`, `Tag`, `SectionHead`, `HeroMeter` — re-created locally in `components/ui/` because cross-project imports aren't viable. `AssetIcon` and `CoverageBar` are Ethena-specific (per-asset reconciliation table cells) and have no equivalent surface here.

### Priority → tone mapping

| Priority | Tone | Token | Use |
|---|---|---|---|
| P0 | risk | `--color-risk` | Drop-everything items. Pulses on the meter when overdue. |
| P1 | warn | `--color-warn` | This-week items. |
| P2 | ok | `--color-ok` | Open but not urgent. |
| P3 | ghost | `--color-text-ghost` | Background noise — visible but unobtrusive. |

This applies everywhere a priority appears: the existing `<PriorityDot>` primitive, queue-section headers, the left-edge accent on cards, the meter fill.

## Layout

The 3-pane Command Center stays exactly as it is structurally. What changes inside each pane:

### Queue panel (left, ~300px)

**Header changes** — `queue-header.tsx`:
- Drop the existing inline-styled bar
- Replace with a compact `<HeroMeter>` at the top showing **overdue P0/P1 count** (items past escalation threshold), with the existing `--color-risk` fill
  - Meter pulses when overdue count > 0
  - Right caption shows `P0: 3 · P1: 4` breakdown in mono
- Below the meter: section filter row (status / source / chatType / search), styled per token system

**Item rendering** — `queue-item.tsx`:
- Each item becomes a **glass card** (`<GlassCard>` wrapper or equivalent inline classes)
- Hover lifts `-translate-y-[1px]` + brightens `--color-bg-card-hover`
- Active (selected) item gets a stronger `--color-border-strong` and slightly higher bg
- Content layout preserved: PriorityDot · name + snippet + meta row (source badge + waiting time)
- Section headers (`queue-section.tsx`) stay flat: `<SectionHead>` with priority count in the status slot using `<Tag>` with the priority tone

### Detail pane (middle, 1fr)

**Conversation area** — `detail-conversation.tsx`, `message-bubble.tsx`:
- Conversation backdrop becomes the same `--color-bg` as the page, plus a subtle inset glow at the top (continuity with the layout's body backdrop)
- Message bubbles: glass treatment. Own messages right-aligned with `--color-bg-elev`; theirs left-aligned with `glass`-style border
- Timestamps in `font-mono text-[10px] text-[var(--color-text-ghost)]`
- Avatars use existing `<Avatar>` primitive (re-styled, see below)

**Reply area** — `reply-area.tsx`:
- Glass surface at the bottom of the conversation
- Textarea inherits `--color-text` on the glass bg, no separate border
- Action row: tone-coded buttons (`<Tag tone="ok">` style for send, `ghost` for snooze/done)

**Empty / loading states** — `detail-pane.tsx`:
- Centred ghost text, same `font-mono text-[var(--color-text-ghost)]` treatment as Ethena's empty states

### Sidebar (right, ~320px)

**Hybrid widget treatment**:
- **Live widgets get `<GlassCard>`** — they update or signal urgency:
  - `scanner-status.tsx`
  - `overdue-alerts.tsx`
  - `calendar-events.tsx`
- **Reference widgets stay flat** — they're stable reference data:
  - `mini-analytics.tsx`
  - `source-breakdown.tsx`
  - `recent-activity.tsx`
  - `inbox-health.tsx` (kept as a sparkline reference widget; the overdue count it implicitly conveys now lives in the queue HeroMeter)

Each widget gets a `<SectionHead>` at top (or a simpler label) and respects the token system for numbers (`font-mono`) and labels (`font-sans uppercase`).

## Files touched

### Add (6 new primitives + spec/plan docs)
- `components/ui/glass-card.tsx`
- `components/ui/tag.tsx`
- `components/ui/section-head.tsx`
- `components/ui/hero-meter.tsx`

*AssetIcon and CoverageBar are NOT ported — they're Ethena-specific (per-asset reconciliation rows). If the catchup domain ever needs them, they can be added later.*

### Modify (existing primitives — adopt new tokens, keep prop shapes)
- `components/ui/avatar.tsx`
- `components/ui/filter-popover.tsx`
- `components/ui/priority-dot.tsx`
- `components/ui/source-badge.tsx`
- `components/ui/waiting-badge.tsx`

### Modify (17 command-center components — inline-style → Tailwind + new tokens)
- `components/command-center/calendar-events.tsx`
- `components/command-center/command-center.tsx`
- `components/command-center/context-sidebar.tsx`
- `components/command-center/detail-conversation.tsx`
- `components/command-center/detail-pane.tsx`
- `components/command-center/inbox-health.tsx`
- `components/command-center/message-bubble.tsx`
- `components/command-center/mini-analytics.tsx`
- `components/command-center/overdue-alerts.tsx`
- `components/command-center/queue-header.tsx` (most changed — HeroMeter integration)
- `components/command-center/queue-item.tsx` (most changed — glass card treatment)
- `components/command-center/queue-panel.tsx`
- `components/command-center/queue-section.tsx`
- `components/command-center/recent-activity.tsx`
- `components/command-center/reply-area.tsx`
- `components/command-center/scanner-status.tsx`
- `components/command-center/source-breakdown.tsx`

### Modify (page / layout / globals)
- `app/globals.css` — full token rewrite (port Ethena's `@theme` block + glass utility + motion keyframes + reduced-motion override)
- `app/layout.tsx` — load Inter + JetBrains Mono via `next/font/google`, add fixed glow backdrop
- `app/page.tsx` — minor: ensure the no-scan empty state uses the new tokens, drop its inline `style={{}}` block
- `app/analytics/page.tsx` — same treatment if present
- `app/login/page.tsx` — adopt the new tokens

## Migration strategy: single PR

One branch — `redesign/monochrome-glass` — handles tokens, primitives, inline-style → Tailwind migration, and visual treatment together. This mirrors the Ethena flow that just shipped. Each batch in the implementation plan leaves the app green; commits are scoped per component so the diff is bisectable.

The two-stage path was rejected because it doubles the touch count on every component (once for mechanical migration, once for visual). The per-batch-PR path was rejected because the user wants the redesign to land cohesively in one merge.

## Hero meter target — at-risk number

The HeroMeter in the queue header shows: **count of P0 items waiting > 24h plus P1 items waiting > 48h**.

- These are the items the bot already escalates on (existing logic in `escalation.py`)
- The meter ratio is `min(1, overdueCount / 5)` — full bar at 5+ overdue, scales linearly below that
- Pulse triggers when `overdueCount > 0` (strict — empty bar doesn't pulse)
- Right caption: `P0: <count> · P1: <count>` to show the breakdown
- Color: `--color-risk` (red) when > 0, `--color-text-ghost` when 0

The current `inbox-health.tsx` widget stays in the sidebar as a 7-day sparkline reference — it now plays a complementary role to the live overdue meter.

## Acceptance criteria

1. Page renders the same data — no items missing, no widgets removed
2. HeroMeter shows correct overdue count, pulses when > 0
3. All four priority levels visible at a glance via dot + section header tone
4. Build passes (`pnpm build`)
5. Lint passes (`pnpm lint`)
6. `prefers-reduced-motion` disables all animations
7. No remaining `style={{}}` objects on any modified component (Tailwind utilities only)
8. Mobile + tablet breakpoints still functional (existing logic preserved)
9. Login page still works (auth flow untouched)

**Note on tests:** The dashboard has zero test infrastructure currently — no vitest, no testing-library, no `tests/` directory. Setting up the test harness is out of scope for this redesign to keep the PR focused. The 6 new primitives ship without unit tests; visual verification in the dev server replaces test coverage for this work. Adding a vitest setup mirroring Ethena's is tracked as a separate follow-up.

## Out of scope (deferred)

- Real-time updates beyond the existing 30-min poll
- Search UX improvements
- New widget types
- Discord / Slack source connectors (separate work tracked in memory)
- View Transitions API on detail-pane swap
- Animating the inbox-health sparkline

## Risks

1. **Inline-style migration scope** — 1797 lines of dashboard code with many inline styles. Easy to lose a state or hover variant in conversion. Mitigation: convert one component at a time, verify each in the running dev server before committing.
2. **next/font/google config drift** — catchup's `app/layout.tsx` doesn't currently load fonts via this path. Adding it means a new Google Fonts dependency. Mitigation: same pattern Ethena uses, proven to work.
3. **Glass blur performance with 50–100 queue items** — every item is a glass card. On low-end devices this could chug. Mitigation: limit `backdrop-filter: blur(16px)` to non-virtualized lists (which catchup is — virtualization is out of scope); if perf becomes an issue post-merge, drop the queue cards' blur and keep border+bg only.
4. **No safety net from tests** — the dashboard has no test infrastructure, so visual regression is caught only by manually checking the dev server after each batch. Mitigation: small commits per component, dev server up during the work, screenshot the home + a few detail states before merging.
