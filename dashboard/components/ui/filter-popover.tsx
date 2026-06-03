"use client";

import { useState, useRef, useEffect } from "react";
import { SOURCE_CONFIG, type Source } from "@/lib/types";

interface FilterPopoverProps {
  currentSource?: string;
  currentChatType?: string;
  onSourceChange: (source: string | undefined) => void;
  onChatTypeChange: (chatType: string | undefined) => void;
}

export function FilterPopover({
  currentSource,
  currentChatType,
  onSourceChange,
  onChatTypeChange,
}: FilterPopoverProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const hasFilters = !!currentSource || !!currentChatType;

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  const sources: Source[] = ["telegram", "notion", "github"];
  const chatTypes = [
    { value: "dm", label: "DMs only" },
    { value: "group", label: "Groups only" },
  ];

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className={[
          "inline-flex items-center gap-2 rounded-md border px-2.5 py-1.5 font-mono text-[10px] transition-colors",
          hasFilters
            ? "border-[var(--color-border-strong)] bg-[var(--color-bg-card-hover)] text-[var(--color-text)]"
            : "border-[var(--color-border)] bg-[var(--color-bg-elev)] text-[var(--color-text-dim)] hover:text-[var(--color-text)]",
        ].join(" ")}
        title="Filters"
      >
        F
      </button>
      {open && (
        <div className="glass absolute right-0 z-50 mt-1 min-w-[180px] p-1">
          <div className="mb-2 px-2 pt-1 font-mono text-[10px] uppercase tracking-[0.05em] text-[var(--color-text-ghost)]">
            Source
          </div>
          {sources.map((s) => (
            <button
              key={s}
              onClick={() => onSourceChange(currentSource === s ? undefined : s)}
              className={[
                "flex w-full cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-[11px]",
                currentSource === s
                  ? "bg-[var(--color-bg-card-hover)] text-[var(--color-text)]"
                  : "text-[var(--color-text-dim)] hover:bg-[var(--color-bg-elev)]",
              ].join(" ")}
            >
              <div
                className="shrink-0 rounded-full"
                style={{
                  width: 6,
                  height: 6,
                  background: SOURCE_CONFIG[s].color,
                }}
              />
              {SOURCE_CONFIG[s].label}
              {currentSource === s && (
                <span className="ml-auto text-[var(--color-ok)]">&#10003;</span>
              )}
            </button>
          ))}
          <div className="my-2 h-px bg-[var(--color-border)]" />
          <div className="mb-2 px-2 font-mono text-[10px] uppercase tracking-[0.05em] text-[var(--color-text-ghost)]">
            Type
          </div>
          {chatTypes.map((t) => (
            <button
              key={t.value}
              onClick={() => onChatTypeChange(currentChatType === t.value ? undefined : t.value)}
              className={[
                "flex w-full cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-[11px]",
                currentChatType === t.value
                  ? "bg-[var(--color-bg-card-hover)] text-[var(--color-text)]"
                  : "text-[var(--color-text-dim)] hover:bg-[var(--color-bg-elev)]",
              ].join(" ")}
            >
              {t.label}
              {currentChatType === t.value && (
                <span className="ml-auto text-[var(--color-ok)]">&#10003;</span>
              )}
            </button>
          ))}
          {hasFilters && (
            <>
              <div className="my-2 h-px bg-[var(--color-border)]" />
              <button
                onClick={() => { onSourceChange(undefined); onChatTypeChange(undefined); }}
                className="w-full rounded-sm px-2 py-1.5 text-center text-[11px] text-[var(--color-risk)] hover:bg-[var(--color-bg-elev)]"
              >
                Clear filters
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
