interface ActivityEntry {
  chat_name: string;
  user_status: string;
  user_status_at: string;
}

interface RecentActivityProps {
  activities: ActivityEntry[];
}

function formatTime(dateStr: string): string {
  return new Date(dateStr).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function actionLabel(status: string): string {
  switch (status) {
    case "done": return "Marked done";
    case "snoozed": return "Snoozed";
    default: return "Updated";
  }
}

function statusColor(status: string): string {
  switch (status) {
    case "done": return "var(--color-ok)";
    case "snoozed": return "var(--color-warn)";
    default: return "var(--color-text-ghost)";
  }
}

export function RecentActivity({ activities }: RecentActivityProps) {
  if (activities.length === 0) return null;

  return (
    <div className="py-3 border-b border-dashed border-[var(--color-border)] last:border-none">
      <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-[var(--color-text-ghost)] mb-2">
        Activity
      </div>
      {activities.map((a, i) => (
        <div
          key={i}
          className="flex items-baseline justify-between py-1 text-[11px]"
        >
          <span className="font-sans text-[var(--color-text)] truncate">
            {a.chat_name}
          </span>
          <span
            className="font-mono text-[10px] shrink-0 ml-2"
            style={{ color: statusColor(a.user_status) }}
          >
            {actionLabel(a.user_status)} · {formatTime(a.user_status_at)}
          </span>
        </div>
      ))}
    </div>
  );
}
