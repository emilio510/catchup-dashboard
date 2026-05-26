"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { FilterPopover } from "@/components/ui/filter-popover";
import { HeroMeter } from "@/components/ui/hero-meter";
import type { Priority } from "@/lib/types";

interface QueueHeaderProps {
  total: number;
  byPriority: Record<Priority, number>;
  currentStatus: string;
  currentSource?: string;
  currentChatType?: string;
  currentSearch?: string;
  overdue: { p0: number; p1: number; total: number };
  meterRatio: number;
}

const REFRESH_INTERVAL_MS = 30 * 60 * 1000;

export function QueueHeader({
  total,
  byPriority,
  currentStatus,
  currentSource,
  currentChatType,
  currentSearch,
  overdue,
  meterRatio,
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
    <div className="border-b border-[var(--color-border)]">
      <div className="border-b border-[var(--color-border)] p-3">
        <HeroMeter
          label="Needs attention"
          ratio={meterRatio}
          valueOverride={
            <>
              {overdue.total}
              <span className="ml-1 font-mono text-[12px] text-[var(--color-text-ghost)]">
                overdue
              </span>
            </>
          }
          rightCaption={
            <>
              P0: {overdue.p0}
              <br />
              P1: {overdue.p1}
            </>
          }
        />
      </div>

      <div className="flex items-center justify-between px-3 pb-2 pt-3.5">
        <div>
          <div className="font-sans text-[16px] font-semibold text-[var(--color-text)]">Catch-up</div>
          <div className="mt-0.5 font-sans text-[11px] text-[var(--color-text-dim)]">{summary}</div>
        </div>
        <button
          onClick={() => router.refresh()}
          className="flex h-7 w-7 items-center justify-center rounded-md border border-[var(--color-border)] bg-transparent text-[11px] text-[var(--color-text-ghost)] transition-all duration-150 hover:border-[var(--color-border-strong)] hover:text-[var(--color-text-dim)]"
          title="Refresh"
        >
          &#x21BB;
        </button>
      </div>

      <div className="flex items-center gap-1 px-3 pb-2">
        {statusTabs.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setFilter("status", tab.value)}
            className={`rounded-md px-2.5 py-1 font-sans text-[11px] font-medium transition-all duration-150 ${
              currentStatus === tab.value
                ? "bg-[var(--color-bg-card-hover)] text-[var(--color-text)]"
                : "bg-transparent text-[var(--color-text-ghost)] hover:text-[var(--color-text-dim)]"
            }`}
          >
            {tab.label}
          </button>
        ))}
        <div className="ml-auto">
          <FilterPopover
            currentSource={currentSource}
            currentChatType={currentChatType}
            onSourceChange={(v) => setFilter("source", v)}
            onChatTypeChange={(v) => setFilter("chatType", v)}
          />
        </div>
      </div>

      <div className="px-3 pb-2.5">
        <input
          type="text"
          value={searchValue}
          onChange={(e) => setSearchValue(e.target.value)}
          placeholder="Search..."
          className="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-bg-elev)] px-2.5 py-1.5 font-sans text-[11px] text-[var(--color-text)] placeholder:text-[var(--color-text-ghost)] focus:border-[var(--color-border-strong)] focus:outline-none"
        />
      </div>
    </div>
  );
}
