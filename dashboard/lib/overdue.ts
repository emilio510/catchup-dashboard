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
