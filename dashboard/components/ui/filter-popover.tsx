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

  const sources: Source[] = ["telegram", "notion", "calendar", "github"];
  const chatTypes = [
    { value: "dm", label: "DMs only" },
    { value: "group", label: "Groups only" },
  ];

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          width: 28,
          height: 28,
          borderRadius: 6,
          border: `1px solid ${hasFilters ? "#3b82f6" : "#1e2a4a"}`,
          background: hasFilters ? "#3b82f615" : "transparent",
          color: hasFilters ? "#60a5fa" : "#64748b",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 12,
          transition: "all 0.15s",
        }}
        title="Filters"
      >
        F
      </button>
      {open && (
        <div
          style={{
            position: "absolute",
            top: 32,
            right: 0,
            width: 200,
            background: "#141b33",
            border: "1px solid #1e2a4a",
            borderRadius: 10,
            padding: 12,
            zIndex: 50,
            boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
          }}
        >
          <div style={{ fontSize: 10, color: "#475569", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 8 }}>
            Source
          </div>
          {sources.map((s) => (
            <button
              key={s}
              onClick={() => onSourceChange(currentSource === s ? undefined : s)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                width: "100%",
                padding: "4px 0",
                background: "none",
                border: "none",
                cursor: "pointer",
                fontSize: 12,
                color: currentSource === s ? "#e2e8f0" : "#64748b",
                textAlign: "left",
              }}
            >
              <div
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  background: SOURCE_CONFIG[s].color,
                }}
              />
              {SOURCE_CONFIG[s].label}
              {currentSource === s && <span style={{ marginLeft: "auto", color: "#60a5fa" }}>&#10003;</span>}
            </button>
          ))}
          <div style={{ height: 1, background: "#1e2a4a", margin: "8px 0" }} />
          <div style={{ fontSize: 10, color: "#475569", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 8 }}>
            Type
          </div>
          {chatTypes.map((t) => (
            <button
              key={t.value}
              onClick={() => onChatTypeChange(currentChatType === t.value ? undefined : t.value)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                width: "100%",
                padding: "4px 0",
                background: "none",
                border: "none",
                cursor: "pointer",
                fontSize: 12,
                color: currentChatType === t.value ? "#e2e8f0" : "#64748b",
                textAlign: "left",
              }}
            >
              {t.label}
              {currentChatType === t.value && <span style={{ marginLeft: "auto", color: "#60a5fa" }}>&#10003;</span>}
            </button>
          ))}
          {hasFilters && (
            <>
              <div style={{ height: 1, background: "#1e2a4a", margin: "8px 0" }} />
              <button
                onClick={() => { onSourceChange(undefined); onChatTypeChange(undefined); }}
                style={{
                  width: "100%",
                  padding: "4px 0",
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  fontSize: 11,
                  color: "#f87171",
                  textAlign: "center",
                }}
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
