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
