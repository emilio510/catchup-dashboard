import { PRIORITY_CONFIG, type Priority } from "@/lib/types";

interface PriorityDotProps {
  priority: Priority;
  size?: number;
}

export function PriorityDot({ priority, size = 6 }: PriorityDotProps) {
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        background: PRIORITY_CONFIG[priority].color,
        flexShrink: 0,
      }}
    />
  );
}
