import { SOURCE_CONFIG, type Source, type TriageItem } from "@/lib/types";

interface SourceBreakdownProps {
  items: TriageItem[];
}

export function SourceBreakdown({ items }: SourceBreakdownProps) {
  const counts: Partial<Record<Source, number>> = {};
  for (const item of items) {
    counts[item.source] = (counts[item.source] ?? 0) + 1;
  }

  const entries = Object.entries(counts)
    .filter(([, count]) => count > 0)
    .sort(([, a], [, b]) => b - a) as [Source, number][];

  if (entries.length === 0) return null;

  const max = Math.max(...entries.map(([, c]) => c));

  return (
    <div>
      <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.5px", color: "#475569", marginBottom: 8 }}>
        Sources
      </div>
      {entries.map(([source, count]) => {
        const config = SOURCE_CONFIG[source];
        return (
          <div key={source} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <span style={{ fontSize: 10, color: "#64748b", width: 36 }}>{config.label}</span>
            <div style={{ flex: 1, height: 6, background: "#162038", borderRadius: 3, overflow: "hidden" }}>
              <div
                style={{
                  height: "100%",
                  width: `${(count / max) * 100}%`,
                  background: config.color,
                  borderRadius: 3,
                  opacity: 0.7,
                }}
              />
            </div>
            <span style={{ fontSize: 10, color: "#64748b", width: 20, textAlign: "right" }}>{count}</span>
          </div>
        );
      })}
    </div>
  );
}
