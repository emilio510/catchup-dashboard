import type { TriageItem } from "@/lib/types";

interface CalendarEventsProps {
  items: TriageItem[];
}

export function CalendarEvents({ items }: CalendarEventsProps) {
  const calendarItems = items.filter((i) => i.source === "calendar");
  if (calendarItems.length === 0) return null;

  return (
    <div>
      <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.5px", color: "#475569", marginBottom: 8 }}>
        Today&apos;s Calendar
      </div>
      {calendarItems.map((item) => {
        const time = item.last_message_at
          ? new Date(item.last_message_at).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false })
          : "";
        return (
          <div
            key={item.id}
            style={{
              background: "#1a2340",
              borderRadius: 6,
              padding: "8px 10px",
              marginBottom: 6,
              borderLeft: "3px solid #4ade80",
            }}
          >
            <div style={{ fontSize: 11, color: "#4ade80", fontWeight: 600 }}>{time}</div>
            <div style={{ fontSize: 12, color: "#e2e8f0", marginTop: 1 }}>{item.chat_name}</div>
          </div>
        );
      })}
    </div>
  );
}
