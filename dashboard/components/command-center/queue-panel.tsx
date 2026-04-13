"use client";

import { Suspense } from "react";
import { QueueHeader } from "./queue-header";
import { QueueSection } from "./queue-section";
import type { Priority, TriageItem } from "@/lib/types";

interface QueuePanelProps {
  items: Record<Priority, TriageItem[]>;
  total: number;
  selectedId: string | null;
  onSelectItem: (item: TriageItem) => void;
  currentStatus: string;
  currentSource?: string;
  currentChatType?: string;
  currentSearch?: string;
}

export function QueuePanel({
  items,
  total,
  selectedId,
  onSelectItem,
  currentStatus,
  currentSource,
  currentChatType,
  currentSearch,
}: QueuePanelProps) {
  const byPriority = {
    P0: items.P0.length,
    P1: items.P1.length,
    P2: items.P2.length,
    P3: items.P3.length,
  };

  return (
    <div
      style={{
        borderRight: "1px solid #1e2a4a",
        background: "#141b33",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      <Suspense fallback={<div style={{ height: 120 }} />}>
        <QueueHeader
          total={total}
          byPriority={byPriority}
          currentStatus={currentStatus}
          currentSource={currentSource}
          currentChatType={currentChatType}
          currentSearch={currentSearch}
        />
      </Suspense>
      <div style={{ flex: 1, overflowY: "auto" }}>
        {(["P0", "P1", "P2", "P3"] as const).map((p) => (
          <QueueSection
            key={p}
            priority={p}
            items={items[p]}
            defaultExpanded={p === "P0" || p === "P1"}
            selectedId={selectedId}
            onSelectItem={onSelectItem}
          />
        ))}
      </div>
    </div>
  );
}
