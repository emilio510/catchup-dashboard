import { PRIORITY_CONFIG, type Priority } from "@/lib/types";

interface PriorityDotProps {
  priority: Priority;
  size?: number;
}

export function PriorityDot({ priority, size = 6 }: PriorityDotProps) {
  return (
    <div
      className="shrink-0 rounded-full"
      style={{
        width: size,
        height: size,
        background: PRIORITY_CONFIG[priority].color,
        boxShadow: priority === "P0" ? "0 0 6px rgba(255,69,58,0.5)" : undefined,
      }}
      aria-hidden
    />
  );
}
