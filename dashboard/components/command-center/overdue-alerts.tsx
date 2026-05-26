import { GlassCard } from "@/components/ui/glass-card";
import { PriorityDot } from "@/components/ui/priority-dot";
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
    <GlassCard className="p-3">
      <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-[var(--color-text-ghost)] mb-2">
        Overdue alerts
      </div>
      <div className="text-[11px] text-[var(--color-risk)] font-medium mb-2">
        {overdue.length} item{overdue.length > 1 ? "s" : ""} overdue
      </div>
      {overdue.map((item) => (
        <button
          key={item.id}
          onClick={() => onSelectItem(item)}
          className="flex items-center justify-between gap-2 py-1 w-full text-left bg-transparent border-none cursor-pointer"
        >
          <span className="flex items-center gap-1.5 min-w-0">
            <PriorityDot priority={item.priority} />
            <span className="font-sans text-[11px] text-[var(--color-text)] truncate">
              {item.chat_name}
            </span>
          </span>
          <span className="font-mono text-[10px] text-[var(--color-text-ghost)] shrink-0">
            {Math.round(item.waiting_days!)}d
          </span>
        </button>
      ))}
    </GlassCard>
  );
}
