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

export function RecentActivity({ activities }: RecentActivityProps) {
  if (activities.length === 0) return null;

  return (
    <div>
      <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.5px", color: "#475569", marginBottom: 8 }}>
        Activity
      </div>
      {activities.map((a, i) => (
        <div
          key={i}
          style={{
            display: "flex",
            gap: 8,
            padding: "4px 0",
            fontSize: 11,
            color: "#64748b",
            borderBottom: i < activities.length - 1 ? "1px solid #162038" : "none",
          }}
        >
          <span style={{ color: "#475569", whiteSpace: "nowrap", flexShrink: 0 }}>
            {formatTime(a.user_status_at)}
          </span>
          <span>
            {actionLabel(a.user_status)} {a.chat_name}
          </span>
        </div>
      ))}
    </div>
  );
}
