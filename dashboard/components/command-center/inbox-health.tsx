"use client";

interface InboxHealthProps {
  data: { date: string; count: number }[];
}

const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function getBarColor(count: number): string {
  if (count === 0) return "var(--color-risk-soft)";
  if (count <= 2) return "var(--color-warn-soft)";
  if (count <= 4) return "var(--color-ok-soft)";
  return "var(--color-ok)";
}

export function InboxHealth({ data }: InboxHealthProps) {
  const days: { label: string; count: number; isToday: boolean }[] = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const dateStr = d.toISOString().split("T")[0];
    const dayName = DAY_NAMES[d.getDay() === 0 ? 6 : d.getDay() - 1];
    const found = data.find((r) => r.date === dateStr);
    days.push({ label: dayName, count: found?.count ?? 0, isToday: i === 0 });
  }

  return (
    <div className="py-3 border-b border-dashed border-[var(--color-border)] last:border-none">
      <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-[var(--color-text-ghost)] mb-2">
        Inbox Health
      </div>
      <div className="flex gap-[3px]">
        {days.map((day) => (
          <div
            key={day.label}
            title={`${day.label}: ${day.count} cleared`}
            className="flex-1 h-6 rounded-sm cursor-default"
            style={{
              background: getBarColor(day.count),
              border: day.isToday
                ? "1px solid var(--color-border-strong)"
                : "1px solid transparent",
            }}
          />
        ))}
      </div>
      <div className="flex gap-[3px] mt-0.5">
        {days.map((day) => (
          <div
            key={day.label}
            className="flex-1 text-center font-mono text-[8px] text-[var(--color-text-ghost)]"
          >
            {day.label}
          </div>
        ))}
      </div>
    </div>
  );
}
