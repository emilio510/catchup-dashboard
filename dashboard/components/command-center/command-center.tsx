"use client";

import { useState } from "react";
import { QueuePanel } from "./queue-panel";
import { DetailPane } from "./detail-pane";
import { ContextSidebar } from "./context-sidebar";
import type { Priority, TriageItem } from "@/lib/types";

interface CommandCenterProps {
  items: Record<Priority, TriageItem[]>;
  total: number;
  currentStatus: string;
  currentSource?: string;
  currentChatType?: string;
  currentSearch?: string;
  scannedAt: string;
  dialogsListed: number;
  dialogsClassified: number;
  inboxHealthData: { date: string; count: number }[];
  analyticsData: { P0: number[]; P1: number[] };
  recentActivity: { chat_name: string; user_status: string; user_status_at: string }[];
}

export function CommandCenter({
  items,
  total,
  currentStatus,
  currentSource,
  currentChatType,
  currentSearch,
  scannedAt,
  dialogsListed,
  dialogsClassified,
  inboxHealthData,
  analyticsData,
  recentActivity,
}: CommandCenterProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const allItems = [...items.P0, ...items.P1, ...items.P2, ...items.P3];
  const selectedItem = selectedId
    ? allItems.find((i) => i.id === selectedId) ?? null
    : null;

  function handleSelectItem(item: TriageItem) {
    setSelectedId(item.id);
  }
  const byPriority = {
    P0: items.P0.length,
    P1: items.P1.length,
    P2: items.P2.length,
    P3: items.P3.length,
  };

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "300px 1fr 320px",
        height: "100vh",
        overflow: "hidden",
      }}
    >
      <QueuePanel
        items={items}
        total={total}
        selectedId={selectedId}
        onSelectItem={handleSelectItem}
        currentStatus={currentStatus}
        currentSource={currentSource}
        currentChatType={currentChatType}
        currentSearch={currentSearch}
      />
      <div style={{ overflow: "hidden" }}>
        <DetailPane item={selectedItem} byPriority={byPriority} total={total} />
      </div>
      <ContextSidebar
        allItems={allItems}
        onSelectItem={handleSelectItem}
        scannedAt={scannedAt}
        dialogsListed={dialogsListed}
        dialogsClassified={dialogsClassified}
        inboxHealthData={inboxHealthData}
        analyticsData={analyticsData}
        recentActivity={recentActivity}
      />
    </div>
  );
}
