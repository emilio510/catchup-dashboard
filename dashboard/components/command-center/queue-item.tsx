"use client";

import { SourceBadge } from "@/components/ui/source-badge";
import { WaitingBadge } from "@/components/ui/waiting-badge";
import { PriorityDot } from "@/components/ui/priority-dot";
import type { TriageItem } from "@/lib/types";

interface QueueItemProps {
  item: TriageItem;
  selected: boolean;
  onSelect: (item: TriageItem) => void;
}

function relativeTime(dateStr: string | null): string {
  if (!dateStr) return "";
  const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
  if (seconds < 60) return "now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  return `${days}d`;
}

export function QueueItem({ item, selected, onSelect }: QueueItemProps) {
  return (
    <button
      onClick={() => onSelect(item)}
      className={`group w-full rounded-[10px] border p-3 text-left backdrop-blur-[16px] transition-all duration-200 ${
        selected
          ? "border-[var(--color-border-strong)] bg-[var(--color-bg-card-hover)]"
          : "border-[var(--color-border)] bg-[var(--color-bg-card)] hover:-translate-y-[1px] hover:border-[var(--color-border-strong)] hover:bg-[var(--color-bg-card-hover)]"
      }`}
    >
      <div className="flex items-start gap-2.5">
        <PriorityDot priority={item.priority} size={6} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <div className="truncate font-sans text-[12px] font-medium text-[var(--color-text)]">
              {item.chat_name}
            </div>
            <div className="shrink-0 font-mono text-[10px] text-[var(--color-text-ghost)]">
              {relativeTime(item.last_message_at)}
            </div>
          </div>
          {item.preview && (
            <div className="mt-1 truncate font-sans text-[11px] text-[var(--color-text-dim)]">
              {item.preview}
            </div>
          )}
          <div className="mt-1.5 flex items-center gap-1.5">
            <SourceBadge source={item.source} />
            <WaitingBadge waitingDays={item.waiting_days} priority={item.priority} />
          </div>
        </div>
      </div>
    </button>
  );
}
