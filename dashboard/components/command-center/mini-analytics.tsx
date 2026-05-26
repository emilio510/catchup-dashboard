import Link from "next/link";

interface MiniAnalyticsProps {
  data: { P0: number[]; P1: number[] };
}

function buildSparklinePath(values: number[], width: number, height: number): string {
  if (values.length < 2) return "";
  const max = Math.max(...values, 1);
  const step = width / (values.length - 1);
  return values
    .map((v, i) => {
      const x = i * step;
      const y = height - (v / max) * height;
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

export function MiniAnalytics({ data }: MiniAnalyticsProps) {
  const combined = data.P0.map((v, i) => v + (data.P1[i] ?? 0));
  const currentP0 = data.P0[data.P0.length - 1] ?? 0;
  const currentP1 = data.P1[data.P1.length - 1] ?? 0;

  return (
    <Link href="/analytics" className="block no-underline">
      <div className="py-3 border-b border-dashed border-[var(--color-border)] last:border-none">
        <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-[var(--color-text-ghost)] mb-2">
          Trend (7d)
        </div>
        {combined.length >= 2 && (
          <svg
            width="100%"
            height="40"
            viewBox="0 0 240 40"
            preserveAspectRatio="none"
            className="mb-1"
          >
            <path
              d={buildSparklinePath(combined, 240, 36)}
              fill="none"
              stroke="rgba(255,255,255,0.45)"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        )}
        <div className="font-mono text-[11px]">
          <span className="text-[var(--color-risk)]">P0: {currentP0}</span>
          {" "}
          <span className="text-[var(--color-warn)]">P1: {currentP1}</span>
        </div>
      </div>
    </Link>
  );
}
