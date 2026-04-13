import { OverdueAlerts } from "./overdue-alerts";
import { SourceBreakdown } from "./source-breakdown";
import { InboxHealth } from "./inbox-health";
import { CalendarEvents } from "./calendar-events";
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
    <div
      style={{
        borderLeft: "1px solid #1e2a4a",
        background: "#141b33",
        padding: 16,
        overflowY: "auto",
        display: "flex",
        flexDirection: "column",
        gap: 20,
      }}
    >
      <OverdueAlerts items={allItems} onSelectItem={onSelectItem} />
      <SourceBreakdown items={allItems} />
      <InboxHealth data={inboxHealthData} />
      <CalendarEvents items={allItems} />
      <ScannerStatus
        scannedAt={scannedAt}
        dialogsListed={dialogsListed}
        dialogsClassified={dialogsClassified}
      />
      <MiniAnalytics data={analyticsData} />
      <RecentActivity activities={recentActivity} />
    </div>
  );
}
