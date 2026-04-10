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

function StatCard({ label, value, color, borderColor }: { label: string; value: number; color: string; borderColor: string }) {
  return (
    <div className="bg-[#161b22] rounded-lg px-5 py-3 text-center" style={{ borderWidth: 1, borderStyle: "solid", borderColor }}>
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
