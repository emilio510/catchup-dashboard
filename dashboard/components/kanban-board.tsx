import { KanbanColumn } from "./kanban-column";
import type { Priority, TriageItem } from "@/lib/types";

interface KanbanBoardProps {
  items: Record<Priority, TriageItem[]>;
}

export function KanbanBoard({ items }: KanbanBoardProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
      {(["P0", "P1", "P2", "P3"] as const).map((priority) => (
        <KanbanColumn key={priority} priority={priority} items={items[priority]} />
      ))}
    </div>
  );
}
