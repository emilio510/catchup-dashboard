import { PRIORITY_CONFIG, type Priority, type TriageItem } from "@/lib/types";
import { TriageCard } from "./triage-card";

interface KanbanColumnProps {
  priority: Priority;
  items: TriageItem[];
}

export function KanbanColumn({ priority, items }: KanbanColumnProps) {
  const config = PRIORITY_CONFIG[priority];

  return (
    <div className="flex flex-col">
      <div className="flex items-center gap-2 mb-3 pb-2" style={{ borderBottomWidth: 2, borderBottomStyle: "solid", borderBottomColor: config.color }}>
        <div className="w-2 h-2 rounded-full" style={{ backgroundColor: config.color }} />
        <span className="font-semibold text-sm">{priority} {config.label}</span>
        <span className="text-[#8b949e] text-xs">({items.length})</span>
      </div>
      <div className="flex flex-col gap-2">
        {items.map((item) => (
          <TriageCard key={item.id} item={item} />
        ))}
        {items.length === 0 && (
          <div className="text-[#8b949e] text-xs py-4 text-center">No items</div>
        )}
      </div>
    </div>
  );
}
