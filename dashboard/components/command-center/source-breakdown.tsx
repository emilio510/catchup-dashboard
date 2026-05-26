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
    <div className="py-3 border-b border-dashed border-[var(--color-border)] last:border-none">
      <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-[var(--color-text-ghost)] mb-2">
        Sources
      </div>
      {entries.map(([source, count]) => {
        const config = SOURCE_CONFIG[source];
        return (
          <div key={source} className="flex items-center justify-between py-1 text-[11px] gap-2">
            <span className="font-sans text-[var(--color-text)] w-10 shrink-0">{config.label}</span>
            <div
              className="flex-1 h-1.5 rounded-full overflow-hidden bg-[var(--color-bg-elev)]"
            >
              <div
                className="h-full rounded-full opacity-70"
                style={{
                  width: `${(count / max) * 100}%`,
                  background: config.color,
                }}
              />
            </div>
            <span className="font-mono text-[var(--color-text-dim)] w-5 text-right">{count}</span>
          </div>
        );
      })}
    </div>
  );
}
