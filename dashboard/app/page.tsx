import { getLatestScan, getTriageItems, getInboxHealthData, getAnalyticsData, getRecentActivity } from "@/lib/db";
import { CommandCenter } from "@/components/command-center/command-center";
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
      <main style={{ maxWidth: 700, margin: "0 auto", padding: "60px 24px", textAlign: "center" }}>
        <div style={{ fontSize: 40, opacity: 0.2, marginBottom: 16 }}>&#9993;</div>
        <h1 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>No scans yet</h1>
        <p style={{ color: "#64748b", fontSize: 13, marginBottom: 16 }}>Run the scanner first:</p>
        <code
          style={{
            display: "block",
            background: "#141b33",
            border: "1px solid #1e2a4a",
            padding: 16,
            borderRadius: 10,
            fontSize: 12,
          }}
        >
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
    />
  );
}
