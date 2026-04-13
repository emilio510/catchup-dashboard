"use client";

import { useState } from "react";
import { PRIORITY_CONFIG, type Priority, type TriageItem } from "@/lib/types";
import { QueueItem } from "./queue-item";

interface QueueSectionProps {
  priority: Priority;
  items: TriageItem[];
  defaultExpanded: boolean;
  selectedId: string | null;
  onSelectItem: (item: TriageItem) => void;
}

export function QueueSection({
  priority,
  items,
  defaultExpanded,
  selectedId,
  onSelectItem,
}: QueueSectionProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const config = PRIORITY_CONFIG[priority];
  const canCollapse = priority === "P2" || priority === "P3";

  return (
    <div>
      <button
        onClick={() => canCollapse && setExpanded(!expanded)}
        className="w-full text-left"
        style={{
          padding: "6px 12px",
          fontSize: 10,
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: "0.5px",
          color: config.color,
          display: "flex",
          alignItems: "center",
          gap: 6,
          borderBottom: `1px solid ${config.color}15`,
          cursor: canCollapse ? "pointer" : "default",
        }}
      >
        <div
          style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: config.color,
          }}
        />
        {config.label}
        <span style={{ fontSize: 10, color: "#475569", fontWeight: 400, marginLeft: "auto" }}>
          {items.length}
          {canCollapse && (
            <span style={{ marginLeft: 4 }}>{expanded ? "\u25BE" : "\u25B8"}</span>
          )}
        </span>
      </button>
      {expanded &&
        items.map((item) => (
          <QueueItem
            key={item.id}
            item={item}
            selected={item.id === selectedId}
            onSelect={onSelectItem}
          />
        ))}
      {expanded && items.length === 0 && (
        <div style={{ padding: "12px", fontSize: 11, color: "#475569", textAlign: "center" }}>
          No items
        </div>
      )}
    </div>
  );
}
