"use client";

import { OverdueAlerts } from "./overdue-alerts";
import { SourceBreakdown } from "./source-breakdown";
import { InboxHealth } from "./inbox-health";
import { ScannerStatus } from "./scanner-status";
import { MiniAnalytics } from "./mini-analytics";
import { RecentActivity } from "./recent-activity";
import type { TriageItem } from "@/lib/types";

interface ContextSidebarProps {
  allItems: TriageItem[];
  onSelectItem: (item: TriageItem) => void;
  scannedAt: string;
  dialogsListed: number;
  dialogsClassified: number;
  inboxHealthData: { date: string; count: number }[];
  analyticsData: { P0: number[]; P1: number[] };
  recentActivity: { chat_name: string; user_status: string; user_status_at: string }[];
}

export function ContextSidebar({
  allItems,
  onSelectItem,
  scannedAt,
  dialogsListed,
  dialogsClassified,
  inboxHealthData,
  analyticsData,
  recentActivity,
}: ContextSidebarProps) {
  return (
    <aside className="flex h-screen flex-col overflow-y-auto border-l border-[var(--color-border)] bg-[var(--color-bg)] px-3">
      {/* Glass widgets — separated by margin */}
      <div className="pt-3 mb-3">
        <OverdueAlerts items={allItems} onSelectItem={onSelectItem} />
      </div>
      <div className="mb-3">
        <ScannerStatus
          scannedAt={scannedAt}
          dialogsListed={dialogsListed}
          dialogsClassified={dialogsClassified}
        />
      </div>

      {/* Flat widgets — each carries its own border-b via the widget root */}
      <SourceBreakdown items={allItems} />
      <InboxHealth data={inboxHealthData} />
      <MiniAnalytics data={analyticsData} />
      <RecentActivity activities={recentActivity} />
    </aside>
  );
}
