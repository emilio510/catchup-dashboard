interface WaitingBadgeProps {
  waitingDays: number | null;
  priority: string;
}

export function WaitingBadge({ waitingDays, priority }: WaitingBadgeProps) {
  if (waitingDays == null || waitingDays < 1) return null;

  const text = `${Math.round(waitingDays)}d wait`;
  const isUrgent = priority === "P0" || priority === "P1";
  if (!isUrgent) return null;

  const toneClass = priority === "P0"
    ? "bg-[var(--color-risk-soft)] text-[var(--color-risk)]"
    : "bg-[var(--color-warn-soft)] text-[var(--color-warn)]";

  return (
    <span
      className={`inline-flex whitespace-nowrap rounded-[3px] px-[5px] py-px font-mono text-[9px] font-semibold ${toneClass}`}
    >
      {text}
    </span>
  );
}
