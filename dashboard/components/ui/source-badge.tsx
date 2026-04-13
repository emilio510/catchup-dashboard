import { SOURCE_CONFIG, type Source } from "@/lib/types";

interface SourceBadgeProps {
  source: Source;
}

export function SourceBadge({ source }: SourceBadgeProps) {
  const config = SOURCE_CONFIG[source];
  return (
    <span
      style={{
        fontSize: 9,
        padding: "1px 5px",
        borderRadius: 3,
        background: `${config.color}15`,
        color: config.color,
        fontWeight: 500,
        letterSpacing: "0.3px",
        whiteSpace: "nowrap",
      }}
    >
      {config.label}
    </span>
  );
}
