import { DetailConversation } from "./detail-conversation";
import type { TriageItem, Priority } from "@/lib/types";

interface DetailPaneProps {
  item: TriageItem | null;
  byPriority: Record<Priority, number>;
  total: number;
}

export function DetailPane({ item, byPriority, total }: DetailPaneProps) {
  if (!item) {
    return (
      <div className="flex h-full flex-col items-center justify-center px-6 py-12 text-center">
        <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-[var(--color-text-ghost)]">
          Select an item
        </div>
        <p className="mt-2 font-sans text-[13px] text-[var(--color-text-dim)]">
          Pick a conversation from the queue to view details.
        </p>
        <div className="mt-3 font-mono text-[11px] text-[var(--color-text-ghost)]">
          {byPriority.P0 > 0 && (
            <span className="text-[var(--color-risk)]">{byPriority.P0} urgent</span>
          )}
          {byPriority.P0 > 0 && byPriority.P1 > 0 && (
            <span className="mx-1">|</span>
          )}
          {byPriority.P1 > 0 && (
            <span className="text-[var(--color-warn)]">{byPriority.P1} this week</span>
          )}
          {(byPriority.P0 > 0 || byPriority.P1 > 0) && (
            <span className="mx-1">|</span>
          )}
          <span>{total} total</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col bg-[var(--color-bg)]">
      <DetailConversation key={item.id} item={item} />
    </div>
  );
}
