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
  overdue: { p0: number; p1: number; total: number };
  meterRatio: number;
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
  overdue,
  meterRatio,
}: QueuePanelProps) {
  const byPriority = {
    P0: items.P0.length,
    P1: items.P1.length,
    P2: items.P2.length,
    P3: items.P3.length,
  };

  return (
    <div className="flex h-screen flex-col overflow-hidden border-r border-[var(--color-border)] bg-[var(--color-bg)]">
      <Suspense fallback={<div className="h-[120px]" />}>
        <QueueHeader
          total={total}
          byPriority={byPriority}
          currentStatus={currentStatus}
          currentSource={currentSource}
          currentChatType={currentChatType}
          currentSearch={currentSearch}
          overdue={overdue}
          meterRatio={meterRatio}
        />
      </Suspense>
      <div className="flex-1 overflow-y-auto">
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
