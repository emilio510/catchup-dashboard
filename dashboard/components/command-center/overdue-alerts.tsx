import type { TriageItem } from "@/lib/types";

interface OverdueAlertsProps {
  items: TriageItem[];
  onSelectItem: (item: TriageItem) => void;
}

export function OverdueAlerts({ items, onSelectItem }: OverdueAlertsProps) {
  const overdue = items.filter((i) => {
    if (!i.waiting_days) return false;
    if (i.priority === "P0" && i.waiting_days >= 1) return true;
    if (i.priority === "P1" && i.waiting_days >= 2) return true;
    return false;
  });

  if (overdue.length === 0) return null;

  return (
    <div
      style={{
        background: "rgba(248,113,113,0.08)",
        border: "1px solid rgba(248,113,113,0.2)",
        borderRadius: 8,
        padding: "10px 12px",
      }}
    >
      <div style={{ fontSize: 12, fontWeight: 600, color: "#f87171", marginBottom: 6 }}>
        {overdue.length} item{overdue.length > 1 ? "s" : ""} overdue
      </div>
      {overdue.map((item) => (
        <button
          key={item.id}
          onClick={() => onSelectItem(item)}
          style={{
            display: "block",
            width: "100%",
            textAlign: "left",
            background: "none",
            border: "none",
            cursor: "pointer",
            fontSize: 11,
            color: "#e2e8f0",
            padding: "2px 0",
          }}
        >
          {item.chat_name}{" "}
          <span style={{ color: "#64748b" }}>
            ({item.priority}, {Math.round(item.waiting_days!)}d)
          </span>
        </button>
      ))}
    </div>
  );
}
