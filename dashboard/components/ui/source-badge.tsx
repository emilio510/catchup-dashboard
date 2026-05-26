import { SOURCE_CONFIG, type Source } from "@/lib/types";

interface SourceBadgeProps {
  source: Source;
}

export function SourceBadge({ source }: SourceBadgeProps) {
  const config = SOURCE_CONFIG[source];
  return (
    <span
      className="inline-flex whitespace-nowrap rounded-[3px] px-[5px] py-px font-mono text-[9px] font-medium tracking-[0.04em]"
      style={{
        background: `${config.color}1f`,
        color: config.color,
      }}
    >
      {config.label}
    </span>
  );
}
