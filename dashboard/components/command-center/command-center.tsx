"use client";

import { useState, useEffect } from "react";
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

type Breakpoint = "desktop" | "tablet" | "mobile";

function useBreakpoint(): Breakpoint {
  const [bp, setBp] = useState<Breakpoint>("desktop");

  useEffect(() => {
    function update() {
      const w = window.innerWidth;
      setBp(w >= 1200 ? "desktop" : w >= 768 ? "tablet" : "mobile");
    }
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);

  return bp;
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
  const bp = useBreakpoint();

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

  // Mobile: show either queue or detail
  if (bp === "mobile") {
    if (selectedItem) {
      return (
        <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
          <div style={{ padding: "8px 12px", borderBottom: "1px solid #1e2a4a", background: "#141b33" }}>
            <button
              onClick={() => setSelectedId(null)}
              style={{
                background: "none",
                border: "none",
                color: "#60a5fa",
                fontSize: 13,
                cursor: "pointer",
                padding: 0,
              }}
            >
              &larr; Back to queue
            </button>
          </div>
          <div style={{ flex: 1, overflow: "auto" }}>
            <DetailPane item={selectedItem} byPriority={byPriority} total={total} />
          </div>
        </div>
      );
    }

    return (
      <div style={{ height: "100vh", overflow: "hidden" }}>
        <QueuePanel
          items={items}
          total={total}
          selectedId={null}
          onSelectItem={handleSelectItem}
          currentStatus={currentStatus}
          currentSource={currentSource}
          currentChatType={currentChatType}
          currentSearch={currentSearch}
        />
      </div>
    );
  }

  // Tablet: queue + detail, no sidebar
  if (bp === "tablet") {
    return (
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "300px 1fr",
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
      </div>
    );
  }

  // Desktop: three panels
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
