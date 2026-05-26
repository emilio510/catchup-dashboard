"use client";

import { useState } from "react";
import { SectionHead } from "@/components/ui/section-head";
import { Tag } from "@/components/ui/tag";
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

  if (items.length === 0) return null;

  return (
    <section className="px-3 py-3">
      <button
        onClick={() => canCollapse && setExpanded(!expanded)}
        className="w-full text-left"
        style={{ cursor: canCollapse ? "pointer" : "default" }}
      >
        <SectionHead
          title={`${priority} · ${config.label}`}
          status={
            <div className="flex items-center gap-1.5">
              <Tag tone={config.tone}>{items.length}</Tag>
              {canCollapse && (
                <span className="font-mono text-[10px] text-[var(--color-text-ghost)]">
                  {expanded ? "▾" : "▸"}
                </span>
              )}
            </div>
          }
        />
      </button>
      {expanded && (
        <div className="flex flex-col gap-2">
          {items.map((item) => (
            <QueueItem
              key={item.id}
              item={item}
              selected={item.id === selectedId}
              onSelect={onSelectItem}
            />
          ))}
        </div>
      )}
    </section>
  );
}
