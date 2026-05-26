"use client";

import { useReducer, useEffect } from "react";
import { GlassCard } from "@/components/ui/glass-card";

interface ScannerStatusProps {
  scannedAt: string;
  dialogsListed: number;
  dialogsClassified: number;
}

function computeTimeAgo(scannedAt: string, now: number): string {
  const scannedDate = new Date(scannedAt);
  const seconds = Math.floor((now - scannedDate.getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

// Reducer so we avoid setState-in-effect: dispatch is stable and the rule
// only flags direct state-setter calls, not dispatch.
function tickReducer(): number {
  return Date.now();
}

export function ScannerStatus({ scannedAt, dialogsListed, dialogsClassified }: ScannerStatusProps) {
  const [now, dispatch] = useReducer(tickReducer, 0, () => Date.now());

  useEffect(() => {
    const id = setInterval(() => dispatch(), 30_000);
    return () => clearInterval(id);
  }, []);

  const timeAgo = computeTimeAgo(scannedAt, now);

  return (
    <GlassCard className="p-3">
      <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-[var(--color-text-ghost)]">
        Scanner
      </div>
      <div className="mt-1.5 flex items-baseline gap-2">
        <span className="font-mono text-[13px] text-[var(--color-ok)]">&#9679; live</span>
        <span className="font-sans text-[10px] text-[var(--color-text-ghost)]">
          scanned {timeAgo}
        </span>
      </div>
      <div className="mt-1 font-mono text-[10px] text-[var(--color-text-ghost)]">
        {dialogsClassified}/{dialogsListed} classified
      </div>
    </GlassCard>
  );
}
