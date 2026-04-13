"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { FilterPopover } from "@/components/ui/filter-popover";
import type { Priority } from "@/lib/types";

interface QueueHeaderProps {
  total: number;
  byPriority: Record<Priority, number>;
  currentStatus: string;
  currentSource?: string;
  currentChatType?: string;
  currentSearch?: string;
}

const REFRESH_INTERVAL_MS = 30 * 60 * 1000;

export function QueueHeader({
  total,
  byPriority,
  currentStatus,
  currentSource,
  currentChatType,
  currentSearch,
}: QueueHeaderProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [searchValue, setSearchValue] = useState(currentSearch ?? "");

  const setFilter = useCallback(
    (key: string, value: string | undefined) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value) {
        params.set(key, value);
      } else {
        params.delete(key);
      }
      router.push(`?${params.toString()}`);
    },
    [router, searchParams]
  );

  useEffect(() => {
    const timeout = setTimeout(() => {
      if (searchValue !== (currentSearch ?? "")) {
        setFilter("search", searchValue || undefined);
      }
    }, 300);
    return () => clearTimeout(timeout);
  }, [searchValue, currentSearch, setFilter]);

  useEffect(() => {
    let hiddenSince: number | null = null;

    const intervalId = setInterval(() => {
      if (!document.hidden) router.refresh();
    }, REFRESH_INTERVAL_MS);

    const handleVisibility = () => {
      if (document.hidden) {
        hiddenSince = Date.now();
      } else if (hiddenSince !== null) {
        if (Date.now() - hiddenSince >= REFRESH_INTERVAL_MS) router.refresh();
        hiddenSince = null;
      }
    };

    document.addEventListener("visibilitychange", handleVisibility);
    return () => {
      clearInterval(intervalId);
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [router]);

  const summaryParts: string[] = [];
  if (byPriority.P0 > 0) summaryParts.push(`${byPriority.P0} urgent`);
  if (byPriority.P1 > 0) summaryParts.push(`${byPriority.P1} this week`);
  const summary = summaryParts.length > 0 ? summaryParts.join(", ") : total > 0 ? `${total} items` : "All clear";

  const statusTabs = [
    { value: "open", label: "To respond" },
    { value: "done", label: "Done" },
    { value: "snoozed", label: "Snoozed" },
  ];

  return (
    <div style={{ borderBottom: "1px solid #1e2a4a" }}>
      <div style={{ padding: "14px 12px 8px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <div style={{ fontSize: 16, fontWeight: 600, color: "#e2e8f0" }}>Catch-up</div>
          <div style={{ fontSize: 11, color: "#64748b", marginTop: 2 }}>{summary}</div>
        </div>
        <button
          onClick={() => router.refresh()}
          style={{
            width: 28,
            height: 28,
            borderRadius: 6,
            border: "1px solid #1e2a4a",
            background: "transparent",
            color: "#64748b",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 11,
            transition: "all 0.15s",
          }}
          title="Refresh"
        >
          &#x21BB;
        </button>
      </div>

      <div style={{ padding: "0 12px 8px", display: "flex", alignItems: "center", gap: 4 }}>
        {statusTabs.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setFilter("status", tab.value)}
            style={{
              padding: "4px 10px",
              borderRadius: 6,
              fontSize: 11,
              fontWeight: 500,
              border: "none",
              cursor: "pointer",
              background: currentStatus === tab.value ? "#3b82f620" : "transparent",
              color: currentStatus === tab.value ? "#60a5fa" : "#64748b",
              transition: "all 0.15s",
            }}
          >
            {tab.label}
          </button>
        ))}
        <div style={{ marginLeft: "auto" }}>
          <FilterPopover
            currentSource={currentSource}
            currentChatType={currentChatType}
            onSourceChange={(v) => setFilter("source", v)}
            onChatTypeChange={(v) => setFilter("chatType", v)}
          />
        </div>
      </div>

      <div style={{ padding: "0 12px 10px" }}>
        <input
          type="text"
          placeholder="Search..."
          value={searchValue}
          onChange={(e) => setSearchValue(e.target.value)}
          style={{
            width: "100%",
            background: "#0c0f1a",
            border: "1px solid #1e2a4a",
            borderRadius: 8,
            padding: "5px 10px",
            fontSize: 11,
            color: "#e2e8f0",
            outline: "none",
          }}
        />
      </div>
    </div>
  );
}
