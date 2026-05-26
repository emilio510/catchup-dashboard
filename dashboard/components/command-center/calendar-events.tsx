import { GlassCard } from "@/components/ui/glass-card";
import type { TriageItem } from "@/lib/types";

interface CalendarEventsProps {
  items: TriageItem[];
}

export function CalendarEvents({ items }: CalendarEventsProps) {
  const calendarItems = items.filter((i) => i.source === "calendar");
  if (calendarItems.length === 0) return null;

  return (
    <GlassCard className="p-3">
      <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-[var(--color-text-ghost)] mb-2">
        Today&apos;s Calendar
      </div>
      {calendarItems.map((item) => {
        const time = item.last_message_at
          ? new Date(item.last_message_at).toLocaleTimeString("en-US", {
              hour: "2-digit",
              minute: "2-digit",
              hour12: false,
            })
          : "";
        return (
          <div key={item.id} className="flex items-baseline gap-2 py-1">
            <span className="font-mono text-[10px] text-[var(--color-text-ghost)] shrink-0 w-12">
              {time}
            </span>
            <span className="font-sans text-[11px] text-[var(--color-text)] truncate">
              {item.chat_name}
            </span>
          </div>
        );
      })}
    </GlassCard>
  );
}
