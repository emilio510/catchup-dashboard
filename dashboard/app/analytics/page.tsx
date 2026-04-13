import { getAnalyticsData } from "@/lib/db";
import { AnalyticsChart } from "@/components/analytics-chart";
import Link from "next/link";

export const dynamic = "force-dynamic";

interface PageProps {
  searchParams: Promise<{
    days?: string;
  }>;
}

export default async function AnalyticsPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const days = parseInt(params.days ?? "30", 10);
  const validDays = [7, 30, 90].includes(days) ? days : 30;

  const data = await getAnalyticsData(validDays);

  return (
    <main style={{ maxWidth: 900, margin: "0 auto", padding: "24px" }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <Link href="/" style={{ fontSize: 13, color: "#64748b", textDecoration: "none" }}>
            &larr; Dashboard
          </Link>
          <h1 style={{ fontSize: 18, fontWeight: 600 }}>Inbox Health</h1>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {[7, 30, 90].map((d) => (
            <Link
              key={d}
              href={`/analytics?days=${d}`}
              style={{
                padding: "5px 12px",
                fontSize: 12,
                borderRadius: 6,
                border: d === validDays ? "1px solid #3b82f6" : "1px solid #1e2a4a",
                color: d === validDays ? "#e2e8f0" : "#64748b",
                background: d === validDays ? "rgba(59,130,246,0.12)" : "transparent",
                textDecoration: "none",
              }}
            >
              {d}d
            </Link>
          ))}
        </div>
      </div>

      {data.labels.length === 0 ? (
        <p style={{ color: "#64748b" }}>No scan data available for this time range.</p>
      ) : (
        <div style={{ background: "#141b33", borderRadius: 10, padding: 24, border: "1px solid #1e2a4a" }}>
          <AnalyticsChart labels={data.labels} datasets={data.datasets} />
        </div>
      )}

      <p style={{ fontSize: 11, color: "#64748b", marginTop: 16 }}>
        Showing open items per priority across {data.labels.length} scans in the last {validDays} days.
      </p>
    </main>
  );
}
