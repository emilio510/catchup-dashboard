interface InboxHealthProps {
  data: { date: string; count: number }[];
}

const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function getColor(count: number): string {
  if (count === 0) return "rgba(248,113,113,0.15)";
  if (count <= 2) return "rgba(251,191,36,0.3)";
  if (count <= 4) return "rgba(74,222,128,0.4)";
  return "rgba(74,222,128,0.6)";
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
    <div>
      <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.5px", color: "#475569", marginBottom: 8 }}>
        Inbox Health
      </div>
      <div style={{ display: "flex", gap: 3 }}>
        {days.map((day) => (
          <div
            key={day.label}
            title={`${day.label}: ${day.count} cleared`}
            style={{
              flex: 1,
              height: 24,
              borderRadius: 3,
              background: getColor(day.count),
              border: day.isToday ? "1px solid #1e2a4a" : "none",
              cursor: "default",
            }}
          />
        ))}
      </div>
      <div style={{ display: "flex", gap: 3, marginTop: 2 }}>
        {days.map((day) => (
          <div key={day.label} style={{ flex: 1, textAlign: "center", fontSize: 8, color: "#475569" }}>
            {day.label}
          </div>
        ))}
      </div>
    </div>
  );
}
