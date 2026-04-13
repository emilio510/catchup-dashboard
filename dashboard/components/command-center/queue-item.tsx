"use client";

import { SourceBadge } from "@/components/ui/source-badge";
import { WaitingBadge } from "@/components/ui/waiting-badge";
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
      className="w-full text-left"
      style={{
        padding: "8px 12px",
        borderBottom: "1px solid #162038",
        display: "flex",
        alignItems: "flex-start",
        gap: 8,
        background: selected ? "#1a2340" : "transparent",
        borderLeft: selected ? "2px solid #60a5fa" : "2px solid transparent",
        transition: "background 0.15s",
        cursor: "pointer",
      }}
      onMouseEnter={(e) => {
        if (!selected) e.currentTarget.style.background = "#141b33";
      }}
      onMouseLeave={(e) => {
        if (!selected) e.currentTarget.style.background = "transparent";
      }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span
            style={{
              fontSize: 12,
              fontWeight: 600,
              color: "#e2e8f0",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
              maxWidth: 160,
            }}
          >
            {item.chat_name}
          </span>
          <SourceBadge source={item.source} />
        </div>
        <div
          style={{
            fontSize: 11,
            color: "#64748b",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
            marginTop: 2,
          }}
        >
          {item.preview}
        </div>
      </div>
      <div style={{ textAlign: "right", flexShrink: 0 }}>
        <div style={{ fontSize: 10, color: "#475569" }}>
          {relativeTime(item.last_message_at)}
        </div>
        <div style={{ marginTop: 2 }}>
          <WaitingBadge waitingDays={item.waiting_days} priority={item.priority} />
        </div>
      </div>
    </button>
  );
}
