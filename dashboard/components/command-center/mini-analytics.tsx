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
    <Link href="/analytics" style={{ textDecoration: "none", display: "block" }}>
      <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.5px", color: "#475569", marginBottom: 8 }}>
        Trend (7d)
      </div>
      {combined.length >= 2 && (
        <svg width="100%" height="40" viewBox="0 0 240 40" preserveAspectRatio="none" style={{ marginBottom: 4 }}>
          <path
            d={buildSparklinePath(combined, 240, 36)}
            fill="none"
            stroke="#60a5fa"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      )}
      <div style={{ fontSize: 11, color: "#64748b" }}>
        <span style={{ color: "#f87171" }}>P0: {currentP0}</span>
        {" "}
        <span style={{ color: "#fbbf24" }}>P1: {currentP1}</span>
      </div>
    </Link>
  );
}
