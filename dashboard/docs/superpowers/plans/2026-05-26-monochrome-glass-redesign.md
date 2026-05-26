# Catchup Dashboard — Monochrome Glass Redesign Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the monochrome-glass house system (per `~/Projects/ethena-flow-monitor/docs/superpowers/specs/2026-05-25-monochrome-glass-redesign-design.md`) to the Catchup Dashboard's 3-pane Command Center, while migrating every component off inline `style={{}}` to Tailwind utility classes.

**Architecture:** Token-first refactor (`app/globals.css` + `app/layout.tsx`), then 4 shared primitives (`components/ui/`), then existing primitive migrations, then a `lib/overdue.ts` helper for the HeroMeter target, then per-pane component rewires (queue → detail → sidebar → page shell).

**Tech Stack:** Next.js 16, Tailwind v4 (`@theme` directive), React 19, Inter + JetBrains Mono via `next/font/google`. **No test infrastructure exists** (no vitest, no testing-library) — verification is build + lint + manual dev-server inspection.

**Spec:** `dashboard/docs/superpowers/specs/2026-05-26-monochrome-glass-redesign-design.md`

**Branch:** `redesign/monochrome-glass` (already created off `main`, currently has the spec commit `0ee3c57`)

**Commit cadence:** One commit per task. After each batch run `pnpm build && pnpm lint` to verify green. Manual visual check in dev server (`pnpm dev` on `localhost:3000`) at batch boundaries — there are no automated regressions to catch you.

---

## Reference: Shared inline-style → Tailwind migration playbook

Multiple tasks reference this verbatim. When migrating a component file:

### Step A: Replace literal hex / rgb colors with CSS variables

The current files use raw hex literals everywhere. Map them to the new token vocabulary:

| Old literal | New value |
|---|---|
| `#0c0f1a`, `#141b33`, `#0f1424` (page/panel bg) | `var(--color-bg)` |
| `#1a2340`, `#1e2a4a` (elevated/border) | `var(--color-bg-elev)` for bg, `var(--color-border)` for borders |
| `#162038`, `#21262d` (dividers) | `var(--color-border)` |
| `#e2e8f0`, `#fff` (text) | `var(--color-text)` |
| `#94a3b8`, `#64748b` (muted text) | `var(--color-text-dim)` |
| `#475569`, `#484f58` (ghost text) | `var(--color-text-ghost)` |
| `#f87171`, `#f85149` (P0/red) | `var(--color-risk)` |
| `#fbbf24`, `#d29922` (P1/amber) | `var(--color-warn)` |
| `#4ade80`, `#3fb950` (P2/green) | `var(--color-ok)` |
| `#60a5fa`, `#388bfd` (accent blue) | `var(--color-text)` (the new system has no accent blue; selection uses brightness, not hue) |
| Per-source colors (`#2AABEE` Telegram, `#7c3aed` Notion, etc.) | **keep as-is** — these are brand identity, not semantic |

### Step B: Replace `style={{}}` inline objects with Tailwind utility classes

Pattern conversion table:

| Inline | Tailwind |
|---|---|
| `style={{ padding: "8px 12px" }}` | `className="px-3 py-2"` |
| `style={{ padding: 16 }}` | `className="p-4"` |
| `style={{ borderRadius: 8 }}` | `className="rounded-lg"` |
| `style={{ borderRadius: 999 }}` | `className="rounded-full"` |
| `style={{ display: "flex", gap: 8 }}` | `className="flex gap-2"` |
| `style={{ display: "grid", gridTemplateColumns: "1fr 1fr" }}` | `className="grid grid-cols-2"` |
| `style={{ fontSize: 12 }}` | `className="text-xs"` (12px) or `text-[12px]` |
| `style={{ fontSize: 10 }}` | `className="text-[10px]"` |
| `style={{ fontWeight: 600 }}` | `className="font-semibold"` |
| `style={{ fontWeight: 500 }}` | `className="font-medium"` |
| `style={{ background: "#xxx" }}` | `className="bg-[var(--color-...)]"` (via tokens) |
| `style={{ color: "#xxx" }}` | `className="text-[var(--color-...)]"` |
| `style={{ border: "1px solid #xxx" }}` | `className="border border-[var(--color-border)]"` |
| `style={{ borderLeft: "2px solid X" }}` | `className="border-l-2 border-[var(--color-risk)]"` (or appropriate tone) |
| `style={{ textAlign: "center" }}` | `className="text-center"` |
| `style={{ cursor: "pointer" }}` | `className="cursor-pointer"` |
| `style={{ transition: "background 0.15s" }}` | `className="transition-colors duration-150"` |

For values that don't have a clean Tailwind class, use arbitrary-value syntax: `className="text-[10.5px]"`, `className="leading-[1.35]"`, etc.

### Step C: Replace inline `onMouseEnter` / `onMouseLeave` hover state with `hover:` classes

Many files use mouse-event handlers to toggle bg color. Replace with Tailwind:

```tsx
// Before
onMouseEnter={(e) => { if (!selected) e.currentTarget.style.background = "#141b33"; }}
onMouseLeave={(e) => { if (!selected) e.currentTarget.style.background = "transparent"; }}

// After
className={`transition-colors ${selected ? "bg-[var(--color-bg-elev)]" : "hover:bg-[var(--color-bg-elev)]"}`}
```

The exception: where hover state needs to coexist with a JS-driven dragging or selection state, keep the handler. Note as a deliberate exception in the commit message.

### Step D: Typography pairing

- Labels, copy, headings, source badges: `font-sans` (set globally on `<body>`)
- Numbers, percentages, addresses, timestamps, monospace: `font-mono`
- Always tabular for numbers: handled globally via `font-variant-numeric: tabular-nums slashed-zero` on body

### Step E: `'use client'` directive

If the file already has `'use client'` at the top, **preserve it**. Don't add or remove the directive — that changes Next.js's rendering semantics.

### What NOT to change in this migration

- Component prop shapes
- Data fetching / `useEffect` logic
- Router / URL state behavior
- Event handler semantics (click → behavior)
- Per-source brand colors (Telegram blue, Notion purple, etc.)

---

## Reference: PRIORITY_CONFIG color migration

The file `lib/types.ts` currently exports:

```ts
export const PRIORITY_CONFIG: Record<Priority, { label: string; color: string }> = {
  P0: { label: "Respond Today", color: "#f87171" },
  P1: { label: "This Week", color: "#fbbf24" },
  P2: { label: "Respond", color: "#4ade80" },
  P3: { label: "Monitor", color: "#94a3b8" },
};
```

The `color` field is consumed by `PriorityDot`, `Avatar`, `WaitingBadge`, and several `command-center/*` files via the literal hex value, often inserted into `style={{}}`. To migrate to the token system, the field becomes a CSS-variable reference string. Browsers happily evaluate `style={{ background: "var(--color-risk)" }}`, so consumer code keeps working unchanged.

```ts
export const PRIORITY_CONFIG: Record<Priority, { label: string; color: string; tone: "risk" | "warn" | "ok" | "ghost" }> = {
  P0: { label: "Respond Today", color: "var(--color-risk)", tone: "risk" },
  P1: { label: "This Week", color: "var(--color-warn)", tone: "warn" },
  P2: { label: "Respond", color: "var(--color-ok)", tone: "ok" },
  P3: { label: "Monitor", color: "var(--color-text-ghost)", tone: "ghost" },
};
```

The new `tone` field gives consumers (e.g. `<Tag>`, queue-section header) a typed handle to pass to the tone prop without parsing the color string. This change is Task 3.1 and must land before Tasks 3.2–3.5 (the primitives that read PRIORITY_CONFIG).

---

## Batch 1 — Foundation tokens + shell

### Task 1.1: Rewrite `app/globals.css`

**Files:**
- Modify: `app/globals.css` (full rewrite)

- [ ] **Step 1: Replace contents with the house token block**

```css
@import "tailwindcss";

@theme {
  /* Surfaces */
  --color-bg: #0a0a0c;
  /* --color-bg-elev = flat surfaces (table rows, list items, hover bg). No border, no blur. */
  --color-bg-elev: rgba(255, 255, 255, 0.03);
  /* --color-bg-card = glass surfaces (used via the .glass utility — pairs with border + blur). */
  --color-bg-card: rgba(255, 255, 255, 0.04);
  --color-bg-card-hover: rgba(255, 255, 255, 0.06);

  /* Borders */
  --color-border: rgba(255, 255, 255, 0.08);
  --color-border-strong: rgba(255, 255, 255, 0.14);
  --color-border-subtle: rgba(255, 255, 255, 0.05);

  /* Text — three tiers */
  --color-text: #f5f5f7;
  --color-text-dim: rgba(255, 255, 255, 0.6);
  --color-text-ghost: rgba(255, 255, 255, 0.35);

  /* Semantic — color reserved for signals only */
  --color-risk: #ff453a;
  --color-risk-soft: rgba(255, 69, 58, 0.12);
  --color-ok: #30d158;
  --color-ok-soft: rgba(48, 209, 88, 0.10);
  --color-warn: #ff9f0a;
  --color-warn-soft: rgba(255, 159, 10, 0.10);

  /* Motion */
  --ease-out: cubic-bezier(0.2, 0.8, 0.2, 1);
  --dur-fast: 200ms;
  --dur-rise: 500ms;
  --dur-meter: 900ms;

  /* Fonts.
     next/font/google in layout.tsx sets --font-sans / --font-mono on the <html>
     element to the loaded font-face name. That declaration has higher cascade
     priority than this @theme block, so it overrides at runtime. */
  --font-sans: -apple-system, system-ui, sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, monospace;
}

html, body {
  background: var(--color-bg);
  color: var(--color-text);
  font-family: var(--font-sans);
  font-variant-numeric: tabular-nums slashed-zero;
}

.tabular {
  font-variant-numeric: tabular-nums slashed-zero;
}

.mono {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums slashed-zero;
}

/* Glass surface utility */
.glass {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-strong);
  border-radius: 12px;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.06),
    0 12px 40px rgba(0, 0, 0, 0.4);
}

/* Motion keyframes */
@keyframes efm-rise {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes efm-fade {
  from { opacity: 0; }
  to { opacity: 1; }
}
@keyframes efm-fill {
  from { width: 0; }
  to { width: var(--efm-fill-to, 100%); }
}
@keyframes efm-risk-pulse {
  0%, 100% { text-shadow: none; }
  50% { text-shadow: 0 0 24px rgba(255, 69, 58, 0.5); }
}
@keyframes efm-glow-pulse {
  0%, 100% { box-shadow: 0 0 8px rgba(255, 69, 58, 0.3); }
  50% { box-shadow: 0 0 18px rgba(255, 69, 58, 0.6); }
}

.efm-rise { opacity: 0; animation: efm-rise var(--dur-rise) var(--ease-out) forwards; }
.efm-fade { opacity: 0; animation: efm-fade var(--dur-fast) var(--ease-out) forwards; }

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

/* Preserve the existing pulse keyframe (used by some existing components) */
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
```

- [ ] **Step 2: Verify build + lint**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard
pnpm build 2>&1 | tail -10
pnpm lint 2>&1 | tail -5
```
Expected: both succeed.

- [ ] **Step 3: Commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/app/globals.css
git commit -m "feat(design): rewrite globals.css to monochrome glass token system"
```

### Task 1.2: Add JetBrains Mono font + glow backdrop in `app/layout.tsx`

**Files:**
- Modify: `dashboard/app/layout.tsx`

- [ ] **Step 1: Replace contents with this**

```tsx
import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const sans = Inter({ subsets: ["latin"], variable: "--font-sans" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: "Catch-up Dashboard",
  description: "Personal priority tracker across Telegram, Notion, GitHub",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`dark ${sans.variable} ${mono.variable}`}>
      <body className="relative min-h-screen overflow-x-hidden bg-[var(--color-bg)] text-[var(--color-text)]">
        {/* Background glows — fixed so they don't scroll with content */}
        <div
          aria-hidden
          className="pointer-events-none fixed -left-32 -top-40 h-[520px] w-[520px] rounded-full bg-white opacity-[0.04] blur-[100px]"
        />
        <div
          aria-hidden
          className="pointer-events-none fixed -right-40 top-[20vh] h-[420px] w-[420px] rounded-full opacity-[0.18] blur-[100px]"
          style={{ background: "var(--color-risk)" }}
        />
        <div className="relative z-10">{children}</div>
      </body>
    </html>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard
pnpm build 2>&1 | tail -10
```
Expected: build succeeds. The first build may take longer than usual while it fetches JetBrains Mono.

- [ ] **Step 3: Commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/app/layout.tsx
git commit -m "feat(design): load Inter + JetBrains Mono, add fixed glow backdrop"
```

---

## Batch 2 — Add 4 shared primitives

### Task 2.1: Add `<GlassCard>`

**Files:**
- Create: `dashboard/components/ui/glass-card.tsx`

- [ ] **Step 1: Create the file with this content**

```tsx
import type { HTMLAttributes } from "react";

export function GlassCard({
  className = "",
  children,
  ...rest
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`glass ${className}`} {...rest}>
      {children}
    </div>
  );
}
```

- [ ] **Step 2: Build + commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -5
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/components/ui/glass-card.tsx
git commit -m "feat(ui): add GlassCard primitive"
```

### Task 2.2: Add `<Tag>`

**Files:**
- Create: `dashboard/components/ui/tag.tsx`

- [ ] **Step 1: Create with this content**

```tsx
type Tone = "ok" | "risk" | "warn" | "ghost";

const TONE_CLASSES: Record<Tone, string> = {
  ok: "bg-[var(--color-ok-soft)] text-[var(--color-ok)] border-[color:rgba(48,209,88,0.25)]",
  risk: "bg-[var(--color-risk-soft)] text-[var(--color-risk)] border-[color:rgba(255,69,58,0.25)]",
  warn: "bg-[var(--color-warn-soft)] text-[var(--color-warn)] border-[color:rgba(255,159,10,0.25)]",
  ghost: "bg-[color:rgba(255,255,255,0.05)] text-[var(--color-text-ghost)] border-[var(--color-border)]",
};

export function Tag({
  tone = "ghost",
  children,
}: {
  tone?: Tone;
  children: React.ReactNode;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md border px-2 py-[3px] font-mono text-[10px] tracking-[0.04em] ${TONE_CLASSES[tone]}`}
    >
      {children}
    </span>
  );
}
```

- [ ] **Step 2: Build + commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -5
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/components/ui/tag.tsx
git commit -m "feat(ui): add Tag primitive with tone API"
```

### Task 2.3: Add `<SectionHead>`

**Files:**
- Create: `dashboard/components/ui/section-head.tsx`

- [ ] **Step 1: Create with this content**

```tsx
export function SectionHead({
  title,
  subtitle,
  status,
}: {
  title: string;
  subtitle?: string;
  status?: React.ReactNode;
}) {
  return (
    <div className="mb-4 flex items-baseline justify-between gap-4">
      <div className="min-w-0">
        <h2 className="text-[12px] font-semibold uppercase tracking-[0.06em] text-[var(--color-text)]">
          {title}
        </h2>
        {subtitle && (
          <p className="mt-1 text-[11px] text-[var(--color-text-ghost)]">{subtitle}</p>
        )}
      </div>
      {status && <div className="shrink-0">{status}</div>}
    </div>
  );
}
```

- [ ] **Step 2: Build + commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -5
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/components/ui/section-head.tsx
git commit -m "feat(ui): add SectionHead primitive"
```

### Task 2.4: Add `<HeroMeter>`

**Files:**
- Create: `dashboard/components/ui/hero-meter.tsx`

- [ ] **Step 1: Create with this content**

```tsx
const DEFAULT_THRESHOLD = 0;

export function HeroMeter({
  label,
  ratio,
  rightCaption,
  threshold = DEFAULT_THRESHOLD,
  valueOverride,
}: {
  label: string;
  /** 0..1 fraction — drives bar fill. */
  ratio: number;
  /** Right-aligned caption (e.g. "P0: 3 · P1: 4"). */
  rightCaption: React.ReactNode;
  /** Pulse when ratio > threshold (strict). Default 0 → pulse on any non-zero. */
  threshold?: number;
  /** When set, displays this string instead of "{pct}%". For showing raw counts. */
  valueOverride?: React.ReactNode;
}) {
  const pct = ratio * 100;
  const fillPct = Math.min(100, Math.max(0, pct));
  const pulse = ratio > threshold;
  const valueStyle = pulse
    ? {
        animation:
          "efm-rise 700ms var(--ease-out) 200ms forwards, efm-risk-pulse 3s ease-in-out 1.5s infinite",
      }
    : {
        animation: "efm-rise 700ms var(--ease-out) 200ms forwards",
      };
  const fillAnimation = pulse
    ? "efm-fill var(--dur-meter) var(--ease-out) 400ms forwards, efm-glow-pulse 3s ease-in-out 1.5s infinite"
    : "efm-fill var(--dur-meter) var(--ease-out) 400ms forwards";
  return (
    <div className="glass flex flex-col justify-between p-[14px]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-[var(--color-text-ghost)]">
            {label}
          </div>
          <div
            data-meter-value
            data-pulse={pulse}
            className="mt-1 font-mono text-[24px] font-light leading-none tracking-[-0.03em] text-[var(--color-risk)] opacity-0"
            style={valueStyle}
          >
            {valueOverride ?? (
              <>
                {pct.toFixed(0)}
                <span className="ml-[2px] text-[16px] text-[var(--color-text-ghost)]">%</span>
              </>
            )}
          </div>
        </div>
        <div className="text-right font-mono text-[10px] leading-[1.5] text-[var(--color-text-ghost)]">
          {rightCaption}
        </div>
      </div>
      <div className="mt-3 h-[6px] overflow-hidden rounded-sm bg-[color:rgba(255,255,255,0.06)]">
        <div
          data-meter-fill
          className="h-full rounded-sm bg-[var(--color-risk)]"
          style={{
            width: 0,
            ["--efm-fill-to" as string]: `${fillPct}%`,
            animation: fillAnimation,
            boxShadow: "0 0 10px rgba(255,69,58,0.4)",
          }}
        />
      </div>
    </div>
  );
}
```

Differences from the Ethena version: smaller font sizes (24px vs 36px), tighter padding (14px vs 18px), added `valueOverride` prop so we can show a raw count (e.g. "7") in the queue header instead of a percentage. Default threshold is `0` so any non-zero count pulses (Ethena's default was `0.2` for percentage-driven contexts).

- [ ] **Step 2: Build + commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -5
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/components/ui/hero-meter.tsx
git commit -m "feat(ui): add HeroMeter primitive with valueOverride for raw counts"
```

---

## Batch 3 — Update types + existing primitives

### Task 3.1: Migrate `lib/types.ts` PRIORITY_CONFIG colors

**Files:**
- Modify: `dashboard/lib/types.ts`

- [ ] **Step 1: Replace the `PRIORITY_CONFIG` block**

Find the existing block:

```ts
export const PRIORITY_CONFIG: Record<Priority, { label: string; color: string }> = {
  P0: { label: "Respond Today", color: "#f87171" },
  P1: { label: "This Week", color: "#fbbf24" },
  P2: { label: "Respond", color: "#4ade80" },
  P3: { label: "Monitor", color: "#94a3b8" },
};
```

Replace with:

```ts
export type Tone = "risk" | "warn" | "ok" | "ghost";

export const PRIORITY_CONFIG: Record<Priority, { label: string; color: string; tone: Tone }> = {
  P0: { label: "Respond Today", color: "var(--color-risk)", tone: "risk" },
  P1: { label: "This Week", color: "var(--color-warn)", tone: "warn" },
  P2: { label: "Respond", color: "var(--color-ok)", tone: "ok" },
  P3: { label: "Monitor", color: "var(--color-text-ghost)", tone: "ghost" },
};
```

The `color` field becomes a CSS variable reference (browsers evaluate `style={{ background: "var(--color-risk)" }}` correctly). The new `tone` field is a typed handle the `<Tag>` primitive accepts directly.

- [ ] **Step 2: Verify build** (existing consumers of `color` still work because CSS variables evaluate in inline styles)

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -10
```
Expected: build green. The page will now render priorities using the new tokens even before the primitives are restyled.

- [ ] **Step 3: Commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/lib/types.ts
git commit -m "refactor(types): map PRIORITY_CONFIG colors to design tokens + add tone"
```

### Task 3.2: Migrate `components/ui/priority-dot.tsx` to Tailwind

**Files:**
- Modify: `dashboard/components/ui/priority-dot.tsx`

- [ ] **Step 1: Replace contents**

```tsx
import { PRIORITY_CONFIG, type Priority } from "@/lib/types";

interface PriorityDotProps {
  priority: Priority;
  size?: number;
}

export function PriorityDot({ priority, size = 6 }: PriorityDotProps) {
  return (
    <div
      className="shrink-0 rounded-full"
      style={{
        width: size,
        height: size,
        background: PRIORITY_CONFIG[priority].color,
        boxShadow: priority === "P0" ? "0 0 6px rgba(255,69,58,0.5)" : undefined,
      }}
      aria-hidden
    />
  );
}
```

The `size` prop is dynamic so width/height stay as inline style. The `boxShadow` on P0 gives the most-urgent dot a subtle glow consistent with the meter pulse.

- [ ] **Step 2: Build + commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -5
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/components/ui/priority-dot.tsx
git commit -m "refactor(ui): migrate PriorityDot to Tailwind + add P0 glow"
```

### Task 3.3: Migrate `components/ui/source-badge.tsx`

**Files:**
- Modify: `dashboard/components/ui/source-badge.tsx`

- [ ] **Step 1: Replace contents**

```tsx
import { SOURCE_CONFIG, type Source } from "@/lib/types";

interface SourceBadgeProps {
  source: Source;
}

export function SourceBadge({ source }: SourceBadgeProps) {
  const config = SOURCE_CONFIG[source];
  return (
    <span
      className="inline-flex whitespace-nowrap rounded-[3px] px-[5px] py-px font-mono text-[9px] font-medium tracking-[0.04em]"
      style={{
        background: `${config.color}1f`,
        color: config.color,
      }}
    >
      {config.label}
    </span>
  );
}
```

The source colors are brand identity (Telegram blue, Notion purple, etc.) — they stay as hex literals via `SOURCE_CONFIG`. The structural CSS (display, padding, radius, font) moves to Tailwind. Background alpha is bumped from `15` (8.6% in hex-pair land) to `1f` (12%) for slightly stronger presence on the darker new bg.

- [ ] **Step 2: Build + commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -5
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/components/ui/source-badge.tsx
git commit -m "refactor(ui): migrate SourceBadge to Tailwind"
```

### Task 3.4: Migrate `components/ui/waiting-badge.tsx`

**Files:**
- Modify: `dashboard/components/ui/waiting-badge.tsx`

- [ ] **Step 1: Replace contents**

```tsx
interface WaitingBadgeProps {
  waitingDays: number | null;
  priority: string;
}

export function WaitingBadge({ waitingDays, priority }: WaitingBadgeProps) {
  if (waitingDays == null || waitingDays < 1) return null;

  const text = `${Math.round(waitingDays)}d wait`;
  const isUrgent = priority === "P0" || priority === "P1";
  if (!isUrgent) return null;

  const toneClass = priority === "P0"
    ? "bg-[var(--color-risk-soft)] text-[var(--color-risk)]"
    : "bg-[var(--color-warn-soft)] text-[var(--color-warn)]";

  return (
    <span
      className={`inline-flex whitespace-nowrap rounded-[3px] px-[5px] py-px font-mono text-[9px] font-semibold ${toneClass}`}
    >
      {text}
    </span>
  );
}
```

- [ ] **Step 2: Build + commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -5
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/components/ui/waiting-badge.tsx
git commit -m "refactor(ui): migrate WaitingBadge to Tailwind with semantic tones"
```

### Task 3.5: Migrate `components/ui/avatar.tsx`

**Files:**
- Modify: `dashboard/components/ui/avatar.tsx`

- [ ] **Step 1: Read the current file to preserve its initials logic**

```bash
cat /Users/akgemilio/Projects/catchup-dashboard/dashboard/components/ui/avatar.tsx
```

You should see `getInitials(name: string)` — keep that function as-is.

- [ ] **Step 2: Replace contents (preserving `getInitials`)**

```tsx
import { PRIORITY_CONFIG, type Priority } from "@/lib/types";

interface AvatarProps {
  name: string;
  priority: Priority;
  size?: number;
}

function getInitials(name: string): string {
  const words = name.split(/\s+/).filter(Boolean);
  if (words.length === 0) return "?";
  if (words.length === 1) return words[0][0].toUpperCase();
  return (words[0][0] + words[words.length - 1][0]).toUpperCase();
}

export function Avatar({ name, priority, size = 36 }: AvatarProps) {
  const color = PRIORITY_CONFIG[priority].color;
  return (
    <div
      className="inline-flex shrink-0 items-center justify-center rounded-full bg-[var(--color-bg-elev)] font-sans font-semibold text-[var(--color-text)]"
      style={{
        width: size,
        height: size,
        border: `2px solid ${color}`,
        fontSize: Math.round(size * 0.38),
      }}
      aria-label={name}
    >
      {getInitials(name)}
    </div>
  );
}
```

The priority ring stays as inline `border` because the color comes from a typed config value (a CSS variable reference, which Tailwind can't easily template into `border-[var(...)]` at arbitrary tones). Size remains inline because it's a runtime prop.

- [ ] **Step 3: Build + commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -5
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/components/ui/avatar.tsx
git commit -m "refactor(ui): migrate Avatar to Tailwind, preserve priority ring"
```

### Task 3.6: Migrate `components/ui/filter-popover.tsx`

**Files:**
- Modify: `dashboard/components/ui/filter-popover.tsx`

- [ ] **Step 1: Read the current file**

```bash
cat /Users/akgemilio/Projects/catchup-dashboard/dashboard/components/ui/filter-popover.tsx
```

This is 159 lines — the most complex existing primitive. Identify:
- The trigger button styling
- The popover container styling
- The option-row styling (selected vs unselected)
- Any keyboard/click-outside logic — KEEP unchanged

- [ ] **Step 2: Apply the Shared inline-style → Tailwind migration playbook**

See the "Reference: Shared inline-style → Tailwind migration playbook" section at the top of this document. Apply Steps A, B, C, D, E to this file. The component's behavior (popover toggle, click-outside, selection) is preserved exactly — only the styling changes.

Specific guidance for this file:
- Trigger button: `inline-flex items-center gap-2 rounded-md border border-[var(--color-border)] bg-[var(--color-bg-elev)] px-2.5 py-1.5 font-mono text-[10px] text-[var(--color-text-dim)] hover:text-[var(--color-text)] transition-colors`
- Popover container: `glass` utility + `absolute z-50 mt-1 min-w-[180px] p-1`
- Option row: `flex items-center gap-2 rounded-sm px-2 py-1.5 text-[11px] cursor-pointer hover:bg-[var(--color-bg-elev)]`; selected state adds `bg-[var(--color-bg-card-hover)] text-[var(--color-text)]`, unselected uses `text-[var(--color-text-dim)]`

- [ ] **Step 3: Build + commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -5
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/components/ui/filter-popover.tsx
git commit -m "refactor(ui): migrate FilterPopover to Tailwind glass styling"
```

---

## Batch 4 — Overdue-count helper

### Task 4.1: Add `lib/overdue.ts` helper

**Files:**
- Create: `dashboard/lib/overdue.ts`

The HeroMeter target is "items past escalation threshold." The Python scanner already enforces these thresholds (P0 > 24h, P1 > 48h) but the dashboard doesn't compute them. This helper provides the counts to the page.

- [ ] **Step 1: Create with this content**

```tsx
import type { TriageItem } from "@/lib/types";

const P0_OVERDUE_HOURS = 24;
const P1_OVERDUE_HOURS = 48;

export interface OverdueCounts {
  p0: number;
  p1: number;
  total: number;
}

/**
 * Counts P0/P1 items past their escalation threshold (24h / 48h respectively).
 * `now` is injectable for testability — defaults to Date.now().
 */
export function computeOverdueCounts(
  items: TriageItem[],
  now: number = Date.now(),
): OverdueCounts {
  let p0 = 0;
  let p1 = 0;
  for (const item of items) {
    if (!item.waiting_since) continue;
    const waitingMs = now - new Date(item.waiting_since).getTime();
    const waitingHours = waitingMs / (1000 * 60 * 60);
    if (item.priority === "P0" && waitingHours > P0_OVERDUE_HOURS) {
      p0++;
    } else if (item.priority === "P1" && waitingHours > P1_OVERDUE_HOURS) {
      p1++;
    }
  }
  return { p0, p1, total: p0 + p1 };
}

/**
 * Ratio to feed HeroMeter: full bar at 5+ overdue, scales linearly below that.
 */
export function overdueRatio(total: number): number {
  return Math.min(1, total / 5);
}
```

- [ ] **Step 2: Build + commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -5
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/lib/overdue.ts
git commit -m "feat(lib): add computeOverdueCounts helper for HeroMeter target"
```

---

## Batch 5 — Queue panel (highest-impact area)

### Task 5.1: Migrate `queue-item.tsx` to glass card per item

**Files:**
- Modify: `dashboard/components/command-center/queue-item.tsx`

This is the most-viewed component in the dashboard. Per the spec, each item becomes a glass card with hover lift.

- [ ] **Step 1: Read current file**

```bash
cat /Users/akgemilio/Projects/catchup-dashboard/dashboard/components/command-center/queue-item.tsx
```

- [ ] **Step 2: Replace contents**

```tsx
"use client";

import { SourceBadge } from "@/components/ui/source-badge";
import { WaitingBadge } from "@/components/ui/waiting-badge";
import { PriorityDot } from "@/components/ui/priority-dot";
import type { TriageItem } from "@/lib/types";

interface QueueItemProps {
  item: TriageItem;
  selected: boolean;
  onSelect: (item: TriageItem) => void;
}

function relativeTime(dateStr: string | null): string {
  if (!dateStr) return "";
  const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
  if (seconds < 60) return "now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  return `${days}d`;
}

export function QueueItem({ item, selected, onSelect }: QueueItemProps) {
  return (
    <button
      onClick={() => onSelect(item)}
      className={`group w-full rounded-[10px] border p-3 text-left backdrop-blur-[16px] transition-all duration-200 ${
        selected
          ? "border-[var(--color-border-strong)] bg-[var(--color-bg-card-hover)]"
          : "border-[var(--color-border)] bg-[var(--color-bg-card)] hover:-translate-y-[1px] hover:border-[var(--color-border-strong)] hover:bg-[var(--color-bg-card-hover)]"
      }`}
    >
      <div className="flex items-start gap-2.5">
        <PriorityDot priority={item.priority} size={6} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <div className="truncate font-sans text-[12px] font-medium text-[var(--color-text)]">
              {item.chat_name}
            </div>
            <div className="shrink-0 font-mono text-[10px] text-[var(--color-text-ghost)]">
              {relativeTime(item.last_message_at)}
            </div>
          </div>
          {item.preview && (
            <div className="mt-1 truncate font-sans text-[11px] text-[var(--color-text-dim)]">
              {item.preview}
            </div>
          )}
          <div className="mt-1.5 flex items-center gap-1.5">
            <SourceBadge source={item.source} />
            <WaitingBadge waitingDays={item.waiting_days} priority={item.priority} />
          </div>
        </div>
      </div>
    </button>
  );
}
```

Key changes from the current implementation:
- Removed all inline `style={{}}` blocks
- Removed `onMouseEnter`/`onMouseLeave` handlers (Tailwind `hover:` classes replace them)
- Glass card surface with hover lift via `hover:-translate-y-[1px]`
- Selected state uses a stronger border and brighter bg instead of a left-border accent
- Preview text added (was missing in the head of the file we read)
- PriorityDot now uses the new primitive

- [ ] **Step 3: Build + commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -5
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/components/command-center/queue-item.tsx
git commit -m "feat(design): queue items become glass cards with hover lift"
```

### Task 5.2: Migrate `queue-section.tsx` to SectionHead + tone-coded counts

**Files:**
- Modify: `dashboard/components/command-center/queue-section.tsx`

- [ ] **Step 1: Read current file**

```bash
cat /Users/akgemilio/Projects/catchup-dashboard/dashboard/components/command-center/queue-section.tsx
```

Note the existing section header layout (priority label + count + collapse toggle if any).

- [ ] **Step 2: Apply the Shared inline-style → Tailwind playbook + use the new primitives**

Replace the section header with `<SectionHead>` from `@/components/ui/section-head`. The count badge becomes a `<Tag>` from `@/components/ui/tag` with `tone` from `PRIORITY_CONFIG[priority].tone`.

Example structure for the rewritten section:

```tsx
import { SectionHead } from "@/components/ui/section-head";
import { Tag } from "@/components/ui/tag";
import { PRIORITY_CONFIG, type Priority, type TriageItem } from "@/lib/types";
import { QueueItem } from "./queue-item";

interface QueueSectionProps {
  priority: Priority;
  items: TriageItem[];
  selectedId: string | null;
  onSelectItem: (item: TriageItem) => void;
}

export function QueueSection({ priority, items, selectedId, onSelectItem }: QueueSectionProps) {
  if (items.length === 0) return null;
  const config = PRIORITY_CONFIG[priority];
  return (
    <section className="px-3 py-3">
      <SectionHead
        title={`${priority} · ${config.label}`}
        status={<Tag tone={config.tone}>{items.length}</Tag>}
      />
      <div className="flex flex-col gap-2">
        {items.map((item) => (
          <QueueItem
            key={item.id}
            item={item}
            selected={item.id === selectedId}
            onSelect={onSelectItem}
          />
        ))}
      </div>
    </section>
  );
}
```

If the current file has additional behaviors (collapse/expand state, drag-and-drop, etc.), preserve them while wrapping the visible UI with `<SectionHead>` and using Tailwind for spacing/colors.

- [ ] **Step 3: Build + commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -5
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/components/command-center/queue-section.tsx
git commit -m "feat(design): queue sections use SectionHead + tone-coded count tag"
```

### Task 5.3: Migrate `queue-panel.tsx` shell

**Files:**
- Modify: `dashboard/components/command-center/queue-panel.tsx`

- [ ] **Step 1: Read current file**

```bash
cat /Users/akgemilio/Projects/catchup-dashboard/dashboard/components/command-center/queue-panel.tsx
```

- [ ] **Step 2: Apply the Shared inline-style → Tailwind playbook**

The panel container moves from inline `style={{ borderRight, background, overflow }}` to:
```tsx
<div className="flex h-screen flex-col overflow-hidden border-r border-[var(--color-border)] bg-[var(--color-bg)]">
```

The scrollable region holding the sections gets `className="flex-1 overflow-y-auto"`. Keep the existing prop signature and `<QueueHeader>` + `<QueueSection>` invocations exactly as they are.

- [ ] **Step 3: Build + commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -5
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/components/command-center/queue-panel.tsx
git commit -m "feat(design): queue panel shell migrates to Tailwind tokens"
```

### Task 5.4: Add `<HeroMeter>` to `queue-header.tsx` + migrate styling

**Files:**
- Modify: `dashboard/components/command-center/queue-header.tsx`
- Modify: `dashboard/components/command-center/queue-panel.tsx` (pass overdue counts down)
- Modify: `dashboard/app/page.tsx` (compute and pass overdue counts to QueuePanel)

This task wires the HeroMeter to the overdue helper. It touches three files because the data has to flow from page → panel → header.

- [ ] **Step 1: Update `app/page.tsx` to compute overdue counts**

Add the import and computation. Locate the existing `Promise.all([...])` block. Below the `byPriority` map, add:

```tsx
import { computeOverdueCounts, overdueRatio } from "@/lib/overdue";

// ... inside the page component, after `const byPriority = ...`:
const overdue = computeOverdueCounts(items);
const meterRatio = overdueRatio(overdue.total);
```

Then pass to `<CommandCenter>`:

```tsx
<CommandCenter
  // ... existing props
  overdue={overdue}
  meterRatio={meterRatio}
/>
```

- [ ] **Step 2: Update `CommandCenter` to thread props through to `QueuePanel`**

In `dashboard/components/command-center/command-center.tsx`, add to the props interface:

```tsx
overdue: { p0: number; p1: number; total: number };
meterRatio: number;
```

Pass them down to every `<QueuePanel>` invocation (there are three — desktop, tablet, mobile branches).

- [ ] **Step 3: Update `QueuePanel` to forward to `QueueHeader`**

In `dashboard/components/command-center/queue-panel.tsx`, add the same two props to its interface and forward them to `<QueueHeader>`.

- [ ] **Step 4: Update `queue-header.tsx`**

Read the file first:

```bash
cat /Users/akgemilio/Projects/catchup-dashboard/dashboard/components/command-center/queue-header.tsx
```

The existing file has search input + filter popovers + a refresh button. Preserve all of that. Add the `<HeroMeter>` as the topmost element of the header.

Add the new props:

```tsx
overdue: { p0: number; p1: number; total: number };
meterRatio: number;
```

Add at the top of the header JSX (before the filter row):

```tsx
import { HeroMeter } from "@/components/ui/hero-meter";

// ... inside return:
<div className="border-b border-[var(--color-border)] p-3">
  <HeroMeter
    label="Needs attention"
    ratio={meterRatio}
    valueOverride={
      <>
        {overdue.total}
        <span className="ml-1 font-mono text-[12px] text-[var(--color-text-ghost)]">
          overdue
        </span>
      </>
    }
    rightCaption={
      <>
        P0: {overdue.p0}
        <br />
        P1: {overdue.p1}
      </>
    }
  />
</div>
```

Then migrate the rest of the existing header content (total count, search input, filter popovers, refresh button) using the Shared inline-style → Tailwind playbook. The search input becomes:

```tsx
<input
  type="text"
  value={searchValue}
  onChange={(e) => setSearchValue(e.target.value)}
  placeholder="Search..."
  className="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-bg-elev)] px-2.5 py-1.5 font-sans text-[11px] text-[var(--color-text)] placeholder:text-[var(--color-text-ghost)] focus:border-[var(--color-border-strong)] focus:outline-none"
/>
```

Keep all the existing `useState`, `useEffect`, `useCallback`, `useRouter`, `useSearchParams` logic exactly as it is — only the styling changes.

- [ ] **Step 5: Build + run dev server to verify**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -15
pnpm dev
```
Open http://localhost:3000 in a browser. Verify:
- HeroMeter shows at the top of the queue panel
- If you have overdue P0/P1 items, the count is non-zero and the value pulses
- Filter popovers + search still work
- Sections render with the new SectionHead + Tag

Ctrl-C the dev server.

- [ ] **Step 6: Commit (all 4 files in one commit since they're tightly coupled)**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/app/page.tsx \
        dashboard/components/command-center/command-center.tsx \
        dashboard/components/command-center/queue-panel.tsx \
        dashboard/components/command-center/queue-header.tsx
git commit -m "feat(design): queue header gets HeroMeter for overdue P0/P1 count"
```

---

## Batch 6 — Detail pane

### Task 6.1: Migrate `message-bubble.tsx`

**Files:**
- Modify: `dashboard/components/command-center/message-bubble.tsx`

- [ ] **Step 1: Read current file**

```bash
cat /Users/akgemilio/Projects/catchup-dashboard/dashboard/components/command-center/message-bubble.tsx
```

- [ ] **Step 2: Apply playbook + glass treatment for received messages**

Per the spec: own messages right-aligned with `--color-bg-elev`, theirs left-aligned with glass-ish border. Read the current props (`{ author, text, ts, isOwn }` or similar).

Target shape:

```tsx
import type { Message } from "@/lib/types";

interface MessageBubbleProps {
  message: Message;
  isOwn: boolean;
}

export function MessageBubble({ message, isOwn }: MessageBubbleProps) {
  return (
    <div className={`flex ${isOwn ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[75%] rounded-2xl px-3 py-2 text-[13px] ${
          isOwn
            ? "bg-[var(--color-bg-elev)] text-[var(--color-text)]"
            : "border border-[var(--color-border)] bg-[var(--color-bg-card)] text-[var(--color-text)] backdrop-blur-[12px]"
        }`}
      >
        <div className="whitespace-pre-wrap font-sans leading-[1.45]">{message.text}</div>
        <div className="mt-1 font-mono text-[9px] text-[var(--color-text-ghost)]">
          {new Date(message.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </div>
      </div>
    </div>
  );
}
```

If the actual prop shape differs from what's assumed above, adapt to whatever the existing file expects and only change the styling. Reading the file in Step 1 is required for that reason.

- [ ] **Step 3: Build + commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -5
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/components/command-center/message-bubble.tsx
git commit -m "feat(design): message bubbles get glass / elev tonal split"
```

### Task 6.2: Migrate `detail-conversation.tsx`

**Files:**
- Modify: `dashboard/components/command-center/detail-conversation.tsx`

- [ ] **Step 1: Read current file**

```bash
cat /Users/akgemilio/Projects/catchup-dashboard/dashboard/components/command-center/detail-conversation.tsx
```

This is 176 lines — the conversation thread renderer. Identify:
- The outer scrollable container
- The header (with chat name, avatar, source badge)
- The message list rendering
- Any sticky elements

- [ ] **Step 2: Apply Shared inline-style → Tailwind playbook**

See the "Reference: Shared inline-style → Tailwind migration playbook" at the top of this document. Apply Steps A, B, C, D, E.

Specific structural changes:
- The outer container becomes `flex h-full flex-col overflow-hidden bg-[var(--color-bg)]`
- The header becomes a sticky strip: `sticky top-0 z-10 border-b border-[var(--color-border)] bg-[color:rgba(10,10,12,0.6)] px-4 py-3 backdrop-blur-[20px]`
- The message list scroll region: `flex-1 overflow-y-auto px-4 py-4`
- Spacing between messages: use `flex flex-col gap-3` on the list wrapper

No structural reorganization beyond this. All event handlers stay.

- [ ] **Step 3: Build + commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -5
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/components/command-center/detail-conversation.tsx
git commit -m "feat(design): detail conversation glass header + Tailwind migration"
```

### Task 6.3: Migrate `reply-area.tsx`

**Files:**
- Modify: `dashboard/components/command-center/reply-area.tsx`

- [ ] **Step 1: Read current file**

```bash
cat /Users/akgemilio/Projects/catchup-dashboard/dashboard/components/command-center/reply-area.tsx
```

This is 181 lines — the reply composition area with draft editing + send button. Identify the form structure.

- [ ] **Step 2: Apply the playbook**

Specific guidance:
- Outer container: `glass m-3 p-3` (glass card at the bottom of the detail pane)
- Textarea: `w-full resize-none bg-transparent font-sans text-[13px] text-[var(--color-text)] placeholder:text-[var(--color-text-ghost)] focus:outline-none`
- Action row: `mt-2 flex items-center justify-between gap-2`
- Send button: `inline-flex items-center gap-1.5 rounded-md bg-[var(--color-ok-soft)] px-2.5 py-1 font-mono text-[11px] font-medium text-[var(--color-ok)] hover:bg-[color:rgba(48,209,88,0.18)] transition-colors`
- Secondary actions (snooze, done): `inline-flex items-center gap-1 rounded-md px-2 py-1 font-mono text-[11px] text-[var(--color-text-ghost)] hover:bg-[var(--color-bg-elev)] hover:text-[var(--color-text)] transition-colors`

Preserve all form submission, draft editing, and server-action logic exactly.

- [ ] **Step 3: Build + commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -5
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/components/command-center/reply-area.tsx
git commit -m "feat(design): reply area becomes glass card with tone-coded actions"
```

### Task 6.4: Migrate `detail-pane.tsx`

**Files:**
- Modify: `dashboard/components/command-center/detail-pane.tsx`

- [ ] **Step 1: Read current file**

```bash
cat /Users/akgemilio/Projects/catchup-dashboard/dashboard/components/command-center/detail-pane.tsx
```

- [ ] **Step 2: Apply playbook**

The detail pane is mostly a shell that switches between empty state and conversation. Apply the playbook for both branches.

Empty state should mirror Ethena's empty-state treatment:

```tsx
<div className="flex h-full flex-col items-center justify-center px-6 py-12 text-center">
  <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-[var(--color-text-ghost)]">
    Select an item
  </div>
  <p className="mt-2 font-sans text-[13px] text-[var(--color-text-dim)]">
    Pick a conversation from the queue to view details.
  </p>
</div>
```

The wrapper for the conversation case: `flex h-full flex-col bg-[var(--color-bg)]`.

- [ ] **Step 3: Build + commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -5
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/components/command-center/detail-pane.tsx
git commit -m "feat(design): detail pane shell migrates to Tailwind tokens"
```

---

## Batch 7 — Sidebar widgets (hybrid treatment)

Per the spec: **live = glass card**, **static = flat section**.

- Live (glass): `scanner-status.tsx`, `overdue-alerts.tsx`, `calendar-events.tsx`
- Static (flat): `mini-analytics.tsx`, `source-breakdown.tsx`, `recent-activity.tsx`, `inbox-health.tsx`

### Task 7.1: Migrate `scanner-status.tsx` (live → glass)

**Files:**
- Modify: `dashboard/components/command-center/scanner-status.tsx`

- [ ] **Step 1: Read current file**

```bash
cat /Users/akgemilio/Projects/catchup-dashboard/dashboard/components/command-center/scanner-status.tsx
```

- [ ] **Step 2: Apply playbook + GlassCard wrapper**

```tsx
import { GlassCard } from "@/components/ui/glass-card";
// ... other imports preserved

// Inside the component, wrap the root element:
<GlassCard className="p-3">
  <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-[var(--color-text-ghost)]">
    Scanner status
  </div>
  <div className="mt-1.5 flex items-baseline gap-2">
    <span className="font-mono text-[13px] text-[var(--color-ok)]">● live</span>
    <span className="font-sans text-[10px] text-[var(--color-text-ghost)]">
      scanned {relativeTime(scannedAt)}
    </span>
  </div>
  {/* ... other existing data preserved */}
</GlassCard>
```

Preserve existing time-formatting helpers and props.

- [ ] **Step 3: Build + commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -5
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/components/command-center/scanner-status.tsx
git commit -m "feat(design): scanner status becomes glass widget"
```

### Task 7.2: Migrate `overdue-alerts.tsx` (live → glass)

**Files:**
- Modify: `dashboard/components/command-center/overdue-alerts.tsx`

- [ ] **Step 1: Read current file**

```bash
cat /Users/akgemilio/Projects/catchup-dashboard/dashboard/components/command-center/overdue-alerts.tsx
```

- [ ] **Step 2: Apply playbook + GlassCard wrapper**

Wrap the root in `<GlassCard className="p-3">`. Apply the Shared playbook. Each alert row uses:
- `flex items-center justify-between gap-2 py-1`
- Left side: small `<PriorityDot priority={item.priority} />` + chat name in `font-sans text-[11px] text-[var(--color-text)]`
- Right side: waiting time in `font-mono text-[10px] text-[var(--color-text-ghost)]`

If there are no overdue items, render an empty-state line: `<span className="font-sans text-[11px] text-[var(--color-text-ghost)]">No overdue items.</span>`.

- [ ] **Step 3: Build + commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -5
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/components/command-center/overdue-alerts.tsx
git commit -m "feat(design): overdue alerts widget becomes glass"
```

### Task 7.3: Migrate `calendar-events.tsx` (live → glass)

**Files:**
- Modify: `dashboard/components/command-center/calendar-events.tsx`

- [ ] **Step 1: Read current file**

```bash
cat /Users/akgemilio/Projects/catchup-dashboard/dashboard/components/command-center/calendar-events.tsx
```

- [ ] **Step 2: Apply playbook + GlassCard wrapper**

Wrap in `<GlassCard className="p-3">`. Each event row:
- `flex items-baseline gap-2 py-1`
- Time in `font-mono text-[10px] text-[var(--color-text-ghost)] shrink-0 w-12`
- Title in `font-sans text-[11px] text-[var(--color-text)] truncate`

- [ ] **Step 3: Build + commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -5
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/components/command-center/calendar-events.tsx
git commit -m "feat(design): calendar events widget becomes glass"
```

### Task 7.4: Migrate `mini-analytics.tsx` (static → flat)

**Files:**
- Modify: `dashboard/components/command-center/mini-analytics.tsx`

- [ ] **Step 1: Read current file**

```bash
cat /Users/akgemilio/Projects/catchup-dashboard/dashboard/components/command-center/mini-analytics.tsx
```

- [ ] **Step 2: Apply playbook (NO GlassCard wrapper — flat section)**

Root: `<div className="py-3 border-b border-dashed border-[var(--color-border)]">` (last widget in the sidebar drops the bottom border via `last:border-none`).

The chart canvas already styles itself. Just migrate any inline `style={{}}` on the label/legend wrappers to Tailwind. Update chart options (if Chart.js is configured here) to use new tokens for grid/line colors: `var(--color-border)` for grid, `var(--color-risk)` / `var(--color-warn)` for P0 / P1 lines.

- [ ] **Step 3: Build + commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -5
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/components/command-center/mini-analytics.tsx
git commit -m "feat(design): mini-analytics widget adopts flat treatment"
```

### Task 7.5: Migrate `source-breakdown.tsx` (static → flat)

**Files:**
- Modify: `dashboard/components/command-center/source-breakdown.tsx`

- [ ] **Step 1: Read current file**

```bash
cat /Users/akgemilio/Projects/catchup-dashboard/dashboard/components/command-center/source-breakdown.tsx
```

- [ ] **Step 2: Apply playbook (flat section, no GlassCard)**

Root: `<div className="py-3 border-b border-dashed border-[var(--color-border)] last:border-none">`. Each row: `flex items-center justify-between py-1 text-[11px]` with source label in `font-sans text-[var(--color-text)]` and count in `font-mono text-[var(--color-text-dim)]`.

- [ ] **Step 3: Build + commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -5
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/components/command-center/source-breakdown.tsx
git commit -m "feat(design): source breakdown widget adopts flat treatment"
```

### Task 7.6: Migrate `recent-activity.tsx` (static → flat)

**Files:**
- Modify: `dashboard/components/command-center/recent-activity.tsx`

- [ ] **Step 1: Read current file**

```bash
cat /Users/akgemilio/Projects/catchup-dashboard/dashboard/components/command-center/recent-activity.tsx
```

- [ ] **Step 2: Apply playbook (flat section, no GlassCard)**

Root: `<div className="py-3 border-b border-dashed border-[var(--color-border)] last:border-none">`. Activity rows: `flex items-baseline justify-between py-1 text-[11px]` — chat name in `font-sans text-[var(--color-text)]`, status + timestamp in `font-mono text-[10px] text-[var(--color-text-ghost)]`. Done/snoozed status uses tone-coded text colors (`text-[var(--color-ok)]` for done, `text-[var(--color-warn)]` for snoozed).

- [ ] **Step 3: Build + commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -5
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/components/command-center/recent-activity.tsx
git commit -m "feat(design): recent activity widget adopts flat treatment"
```

### Task 7.7: Migrate `inbox-health.tsx` (static → flat sparkline)

**Files:**
- Modify: `dashboard/components/command-center/inbox-health.tsx`

- [ ] **Step 1: Read current file**

```bash
cat /Users/akgemilio/Projects/catchup-dashboard/dashboard/components/command-center/inbox-health.tsx
```

- [ ] **Step 2: Apply playbook (flat section, no GlassCard)**

Root: `<div className="py-3 border-b border-dashed border-[var(--color-border)] last:border-none">`. Sparkline bars: update inline bar colors to `var(--color-text-ghost)` for normal days, `var(--color-warn)` or `var(--color-risk)` for spike days. Label uses `text-[10px] font-medium uppercase tracking-[0.14em] text-[var(--color-text-ghost)]`.

- [ ] **Step 3: Build + commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -5
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/components/command-center/inbox-health.tsx
git commit -m "feat(design): inbox-health sparkline adopts flat treatment"
```

### Task 7.8: Migrate `context-sidebar.tsx` (wrapper)

**Files:**
- Modify: `dashboard/components/command-center/context-sidebar.tsx`

- [ ] **Step 1: Read current file**

```bash
cat /Users/akgemilio/Projects/catchup-dashboard/dashboard/components/command-center/context-sidebar.tsx
```

This is the sidebar wrapper. Apply the playbook:

Root: `<aside className="flex h-screen flex-col overflow-hidden border-l border-[var(--color-border)] bg-[var(--color-bg)] px-3 overflow-y-auto">`. The widgets list naturally separates via each widget's `border-b border-dashed` (the flat ones) or `mb-3` spacing (the glass ones).

If the sidebar currently has its own section headers between widgets, replace each with `<SectionHead title="..." />`.

- [ ] **Step 2: Build + commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -5
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/components/command-center/context-sidebar.tsx
git commit -m "feat(design): context sidebar shell migrates to Tailwind tokens"
```

---

## Batch 8 — Page shell + auxiliary pages

### Task 8.1: Migrate `command-center.tsx` 3-pane shell

**Files:**
- Modify: `dashboard/components/command-center/command-center.tsx`

- [ ] **Step 1: Read current file** (already saw partial content above)

```bash
cat /Users/akgemilio/Projects/catchup-dashboard/dashboard/components/command-center/command-center.tsx
```

- [ ] **Step 2: Migrate all 3 layout branches (desktop, tablet, mobile) to Tailwind**

Desktop (3-pane):
```tsx
<div className="grid h-screen grid-cols-[300px_1fr_320px] overflow-hidden">
```

Tablet (2-pane):
```tsx
<div className="grid h-screen grid-cols-[300px_1fr] overflow-hidden">
```

Mobile back-button bar:
```tsx
<div className="flex h-screen flex-col">
  <div className="border-b border-[var(--color-border)] bg-[color:rgba(10,10,12,0.6)] px-3 py-2 backdrop-blur-[20px]">
    <button
      onClick={() => setSelectedId(null)}
      className="bg-transparent text-[13px] text-[var(--color-text-dim)] hover:text-[var(--color-text)]"
    >
      ← Back to queue
    </button>
  </div>
  <div className="flex-1 overflow-auto">
    {/* DetailPane */}
  </div>
</div>
```

Preserve `useBreakpoint()` hook and all conditional rendering. Only styling changes.

- [ ] **Step 3: Build + commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -5
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/components/command-center/command-center.tsx
git commit -m "feat(design): command center 3-pane shell migrates to Tailwind"
```

### Task 8.2: Migrate `app/page.tsx` empty state

**Files:**
- Modify: `dashboard/app/page.tsx`

The page already got partial updates in Task 5.4 (overdue counts). This task cleans up the remaining inline-styled empty state.

- [ ] **Step 1: Replace the "No scans yet" empty-state JSX**

Find the existing block (starts with `<main style={{ maxWidth: 700, ...`). Replace with:

```tsx
<main className="mx-auto max-w-[700px] px-6 py-16 text-center">
  <div className="mb-4 font-mono text-[40px] text-[var(--color-text-ghost)]">✉</div>
  <h1 className="font-sans text-[18px] font-semibold text-[var(--color-text)]">No scans yet</h1>
  <p className="mt-2 font-sans text-[13px] text-[var(--color-text-dim)]">Run the scanner first:</p>
  <code className="mt-4 block rounded-[10px] border border-[var(--color-border)] bg-[var(--color-bg-elev)] p-4 font-mono text-[12px] text-[var(--color-text)]">
    cd scanner && python -m src.cli --config config.yaml --no-digest
  </code>
</main>
```

- [ ] **Step 2: Build + commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -5
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/app/page.tsx
git commit -m "feat(design): page empty state adopts new tokens"
```

### Task 8.3: Migrate `app/login/page.tsx`

**Files:**
- Modify: `dashboard/app/login/page.tsx`

- [ ] **Step 1: Read current file**

```bash
cat /Users/akgemilio/Projects/catchup-dashboard/dashboard/app/login/page.tsx
```

- [ ] **Step 2: Apply playbook**

Centered single-card login form. Target shape:

```tsx
<main className="flex min-h-screen items-center justify-center px-6">
  <form
    onSubmit={...}  // preserve
    className="glass w-full max-w-[400px] p-6"
  >
    <h1 className="font-sans text-[18px] font-semibold text-[var(--color-text)]">Sign in</h1>
    <p className="mt-1 font-sans text-[12px] text-[var(--color-text-dim)]">Enter the dashboard password.</p>
    <input
      type="password"
      // preserve other props
      className="mt-4 w-full rounded-md border border-[var(--color-border)] bg-[var(--color-bg-elev)] px-3 py-2 font-sans text-[13px] text-[var(--color-text)] placeholder:text-[var(--color-text-ghost)] focus:border-[var(--color-border-strong)] focus:outline-none"
    />
    {error && (
      <p className="mt-2 font-mono text-[11px] text-[var(--color-risk)]">{error}</p>
    )}
    <button
      type="submit"
      className="mt-4 w-full rounded-md bg-[var(--color-ok-soft)] py-2 font-mono text-[12px] font-medium text-[var(--color-ok)] hover:bg-[color:rgba(48,209,88,0.18)] transition-colors"
    >
      Sign in
    </button>
  </form>
</main>
```

Preserve all auth logic — only styling changes.

- [ ] **Step 3: Build + commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -5
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/app/login/page.tsx
git commit -m "feat(design): login page adopts glass card treatment"
```

### Task 8.4: Migrate `app/analytics/page.tsx`

**Files:**
- Modify: `dashboard/app/analytics/page.tsx`

- [ ] **Step 1: Read current file**

```bash
cat /Users/akgemilio/Projects/catchup-dashboard/dashboard/app/analytics/page.tsx
```

- [ ] **Step 2: Apply playbook**

Target shell:

```tsx
<main className="mx-auto max-w-[900px] px-6 py-6">
  <div className="mb-6 flex items-baseline justify-between">
    <div className="flex items-center gap-4">
      <Link href="/" className="font-mono text-[11px] text-[var(--color-text-ghost)] no-underline hover:text-[var(--color-text)]">
        ← Dashboard
      </Link>
      <h1 className="font-sans text-[18px] font-semibold text-[var(--color-text)]">Inbox Health</h1>
    </div>
    <div className="flex gap-2">
      {[7, 30, 90].map((d) => (
        <Link
          key={d}
          href={`?days=${d}`}
          className={`rounded-md px-2.5 py-1 font-mono text-[11px] transition-colors ${
            d === validDays
              ? "bg-[var(--color-bg-elev)] text-[var(--color-text)]"
              : "text-[var(--color-text-ghost)] hover:text-[var(--color-text)]"
          }`}
        >
          {d}d
        </Link>
      ))}
    </div>
  </div>
  <div className="glass p-4">
    <AnalyticsChart data={data} />
  </div>
</main>
```

If `AnalyticsChart` itself uses Chart.js with old colors, update those too (or defer to a follow-up if it's complex).

- [ ] **Step 3: Build + commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -5
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/app/analytics/page.tsx
git commit -m "feat(design): analytics page adopts new tokens + glass chart card"
```

### Task 8.5: Migrate `components/analytics-chart.tsx`

**Files:**
- Modify: `dashboard/components/analytics-chart.tsx`

- [ ] **Step 1: Read current file**

```bash
cat /Users/akgemilio/Projects/catchup-dashboard/dashboard/components/analytics-chart.tsx
```

- [ ] **Step 2: Update chart colors to use new tokens**

Update the Chart.js options to use:
- Grid color: `rgba(255, 255, 255, 0.06)`
- Tick color: `rgba(255, 255, 255, 0.35)` (= `--color-text-ghost`)
- Line colors: `#ff453a` for P0, `#ff9f0a` for P1, `#30d158` for P2, `rgba(255, 255, 255, 0.45)` for P3
- Font family: `'JetBrains Mono', ui-monospace, monospace` for axis labels
- Tooltip bg: `rgba(10, 10, 12, 0.95)`, border: `rgba(255, 255, 255, 0.14)`

Chart.js doesn't read CSS variables, so the hex/rgba literals are necessary here. Comment them with the matching token names for future maintenance.

- [ ] **Step 3: Build + commit**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard && pnpm build 2>&1 | tail -5
cd /Users/akgemilio/Projects/catchup-dashboard
git add dashboard/components/analytics-chart.tsx
git commit -m "feat(design): analytics chart colors adopt token palette"
```

---

## Batch 9 — Polish, cleanup, verification

### Task 9.1: Hunt remaining inline styles + hex literals

- [ ] **Step 1: Grep for stragglers**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard
grep -rn "style={{" components app 2>/dev/null | grep -v "^Binary"
```

Each match needs justification — either it's a runtime-dynamic value (width/height from props, animation override) which is legitimate, or it's leftover from migration which needs fixing.

Then:

```bash
grep -rEn "#[0-9a-fA-F]{3,8}" components app 2>/dev/null | grep -v "node_modules" | grep -vE "(#fff|#000|SOURCE_CONFIG|chart-color-comment)" | head -40
```

Any hex literal in the source (outside Chart.js color comments and the per-source brand colors in `lib/types.ts`) should be a token. Convert each.

- [ ] **Step 2: Fix any stragglers found**

For each result, either:
- Convert to a Tailwind utility / arbitrary-value class
- Replace the hex with `var(--color-...)` if it's in an inline style
- Add a justification comment if it's a runtime-dynamic value (e.g. `// width comes from prop`)

Commit each fix or batch in a single commit:

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git add -A
git commit -m "chore(design): clean up remaining inline styles and hex literals"
```

(Skip the commit if there are zero stragglers — that's a good sign.)

### Task 9.2: Final build + manual sanity sweep

- [ ] **Step 1: Clean build**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard/dashboard
rm -rf .next
pnpm build 2>&1 | tail -25
pnpm lint 2>&1 | tail -10
```
Expected: both green.

- [ ] **Step 2: Run dev server and sanity-check**

```bash
pnpm dev
```
Open http://localhost:3000 and verify:
- Login page renders with glass card
- After login, the 3-pane Command Center renders
- HeroMeter shows at top of Queue panel; if there are overdue P0/P1 items, the count pulses
- Queue items render as glass cards with hover lift
- Clicking an item opens the conversation in the detail pane
- Sidebar shows glass widgets (scanner status, overdue alerts, calendar) and flat widgets (mini-analytics, source breakdown, recent activity, inbox-health)
- Filter popovers + search still work
- Mobile view (resize to <768px): single pane with back-button
- Tablet view (768–1199px): 2-pane (no sidebar)
- Analytics page at `/analytics` renders the chart with new tokens

Ctrl-C the dev server.

- [ ] **Step 3: Diff summary**

```bash
cd /Users/akgemilio/Projects/catchup-dashboard
git log --oneline main..HEAD
```

Expected: ~30 commits covering tokens → primitives → existing-primitive migrations → overdue helper → queue → detail → sidebar → page shell → auxiliary → cleanup.

- [ ] **Step 4: No commit needed** — branch is ready for review or merge.

---

## Plan summary

- **9 batches** producing **~30 commits**, each leaving the app green
- **4 new shared primitives** (`GlassCard`, `Tag`, `SectionHead`, `HeroMeter`)
- **5 existing primitives** migrated (`PriorityDot`, `SourceBadge`, `WaitingBadge`, `Avatar`, `FilterPopover`)
- **17 command-center components** migrated from inline styles to Tailwind tokens + design system
- **3 app routes** (`/`, `/login`, `/analytics`) restyled
- **1 new helper** (`lib/overdue.ts`) wired to the HeroMeter
- **Zero data / scanner / API changes** — pure cosmetic refactor + style migration
- **Risk surface**: backdrop-filter performance on long queue lists (mitigation: drop the per-item blur and keep border+bg if it chugs); no test safety net (mitigation: dev-server check between batches)

Total estimated effort: 6–8 hours of focused work for a developer fresh to the codebase.
