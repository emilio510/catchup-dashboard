"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, useCallback } from "react";

const REFRESH_INTERVAL_MS = 30 * 60 * 1000; // 30 minutes
const DISPLAY_UPDATE_MS = 60 * 1000; // 1 minute

export function AutoRefresh() {
  const router = useRouter();
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());
  const [timeAgo, setTimeAgo] = useState("just now");

  const refresh = useCallback(() => {
    router.refresh();
    setLastRefreshed(new Date());
  }, [router]);

  // Auto-refresh every 30 minutes, skip if tab is hidden
  useEffect(() => {
    let intervalId: ReturnType<typeof setInterval>;
    let hiddenSince: number | null = null;

    const startInterval = () => {
      intervalId = setInterval(() => {
        if (document.hidden) {
          return;
        }
        refresh();
      }, REFRESH_INTERVAL_MS);
    };

    const handleVisibilityChange = () => {
      if (document.hidden) {
        hiddenSince = Date.now();
      } else if (hiddenSince !== null) {
        const elapsed = Date.now() - hiddenSince;
        hiddenSince = null;
        if (elapsed >= REFRESH_INTERVAL_MS) {
          refresh();
        }
      }
    };

    startInterval();
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      clearInterval(intervalId);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [refresh]);

  // Update display string every minute
  useEffect(() => {
    const update = () => {
      const seconds = Math.floor((Date.now() - lastRefreshed.getTime()) / 1000);
      if (seconds < 60) {
        setTimeAgo("just now");
      } else {
        const minutes = Math.floor(seconds / 60);
        setTimeAgo(`${minutes}m ago`);
      }
    };

    update();
    const id = setInterval(update, DISPLAY_UPDATE_MS);
    return () => clearInterval(id);
  }, [lastRefreshed]);

  return (
    <div className="flex items-center gap-2 text-sm text-[#8b949e]">
      <span>Refreshed: {timeAgo}</span>
      <button
        onClick={refresh}
        className="px-2 py-1 text-xs rounded border border-[#30363d] hover:border-[#8b949e] transition-colors"
        title="Refresh now"
      >
        Refresh
      </button>
    </div>
  );
}
