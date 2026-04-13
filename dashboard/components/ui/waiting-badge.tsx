interface WaitingBadgeProps {
  waitingDays: number | null;
  priority: string;
}

export function WaitingBadge({ waitingDays, priority }: WaitingBadgeProps) {
  if (waitingDays == null || waitingDays < 1) return null;

  const text = `${Math.round(waitingDays)}d wait`;
  const isUrgent = priority === "P0" || priority === "P1";
  const color = priority === "P0" ? "#f87171" : "#fbbf24";

  if (!isUrgent) return null;

  return (
    <span
      style={{
        fontSize: 9,
        padding: "1px 5px",
        borderRadius: 3,
        background: `${color}15`,
        color,
        fontWeight: 600,
        whiteSpace: "nowrap",
      }}
    >
      {text}
    </span>
  );
}
