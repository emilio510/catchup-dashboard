import { getLatestScan, getTriageItems, getInboxHealthData, getAnalyticsData, getRecentActivity } from "@/lib/db";
import { CommandCenter } from "@/components/command-center/command-center";
import { computeOverdueCounts, overdueRatio } from "@/lib/overdue";
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
      <main className="mx-auto max-w-[700px] px-6 py-16 text-center">
        <h1 className="font-sans text-[18px] font-semibold text-[var(--color-text)]">No scans yet</h1>
        <p className="mt-2 font-sans text-[13px] text-[var(--color-text-dim)]">Run the scanner first:</p>
        <code className="mt-4 block rounded-[10px] border border-[var(--color-border)] bg-[var(--color-bg-elev)] p-4 font-mono text-[12px] text-[var(--color-text)]">
          cd scanner && python -m src.cli --config config.yaml --no-digest
        </code>
      </main>
    );
  }

  const status = params.status ?? "open";

  const [items, inboxHealthData, analyticsRaw, recentActivity] = await Promise.all([
    getTriageItems({
      userStatus: status,
      source: params.source,
      chatType: params.chatType,
      search: params.search,
    }),
    getInboxHealthData(7),
    getAnalyticsData(7),
    getRecentActivity(5),
  ]);

  const byPriority: Record<Priority, typeof items> = {
    P0: items.filter((i) => i.priority === "P0"),
    P1: items.filter((i) => i.priority === "P1"),
    P2: items.filter((i) => i.priority === "P2"),
    P3: items.filter((i) => i.priority === "P3"),
  };

  const overdue = computeOverdueCounts(items);
  const meterRatio = overdueRatio(overdue.total);

  return (
    <CommandCenter
      items={byPriority}
      total={items.length}
      currentStatus={status}
      currentSource={params.source}
      currentChatType={params.chatType}
      currentSearch={params.search}
      scannedAt={scan.scanned_at}
      dialogsListed={scan.dialogs_listed}
      dialogsClassified={scan.dialogs_classified}
      inboxHealthData={inboxHealthData}
      analyticsData={{ P0: analyticsRaw.datasets.P0, P1: analyticsRaw.datasets.P1 }}
      recentActivity={recentActivity}
      overdue={overdue}
      meterRatio={meterRatio}
    />
  );
}
