import { getAnalyticsData } from "@/lib/db";
import { AnalyticsChart } from "@/components/analytics-chart";
import Link from "next/link";
import { GlassCard } from "@/components/ui/glass-card";

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
    <main className="mx-auto max-w-[900px] px-6 py-6">
      <div className="mb-6 flex items-baseline justify-between">
        <div className="flex items-center gap-4">
          <Link href="/" className="font-mono text-[11px] text-[var(--color-text-ghost)] no-underline hover:text-[var(--color-text)]">
            &larr; Dashboard
          </Link>
          <h1 className="font-sans text-[18px] font-semibold text-[var(--color-text)]">Inbox Health</h1>
        </div>
        <div className="flex gap-2">
          {[7, 30, 90].map((d) => (
            <Link
              key={d}
              href={`?days=${d}`}
              className={`rounded-md px-2.5 py-1 font-mono text-[11px] transition-colors ${
                d === validDays
                  ? "bg-[var(--color-bg-elev)] text-[var(--color-text)]"
                  : "text-[var(--color-text-ghost)] hover:text-[var(--color-text)]"
              }`}
            >
              {d}d
            </Link>
          ))}
        </div>
      </div>

      {data.labels.length === 0 ? (
        <p className="font-sans text-[13px] text-[var(--color-text-dim)]">No scan data available for this time range.</p>
      ) : (
        <GlassCard className="p-4">
          <AnalyticsChart labels={data.labels} datasets={data.datasets} />
        </GlassCard>
      )}

      <p className="mt-4 font-mono text-[11px] text-[var(--color-text-ghost)]">
        Showing open items per priority across {data.labels.length} scans in the last {validDays} days.
      </p>
    </main>
  );
}
