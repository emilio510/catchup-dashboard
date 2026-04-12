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
    <main className="max-w-7xl mx-auto px-6 py-8">
      <div className="flex items-baseline justify-between mb-6">
        <div className="flex items-center gap-4">
          <Link href="/" className="text-sm text-[#8b949e] hover:text-[#e6edf3] transition-colors">
            &larr; Dashboard
          </Link>
          <h1 className="text-xl font-bold">Inbox Health</h1>
        </div>
        <div className="flex gap-2">
          {[7, 30, 90].map((d) => (
            <Link
              key={d}
              href={`/analytics?days=${d}`}
              className={`px-3 py-1 text-sm rounded border transition-colors ${
                d === validDays
                  ? "border-[#1f6feb] text-[#e6edf3] bg-[#1f6feb]/20"
                  : "border-[#30363d] text-[#8b949e] hover:border-[#8b949e]"
              }`}
            >
              {d}d
            </Link>
          ))}
        </div>
      </div>

      {data.labels.length === 0 ? (
        <p className="text-[#8b949e]">No scan data available for this time range.</p>
      ) : (
        <div className="bg-[#161b22] rounded-lg p-6 border border-[#30363d]">
          <AnalyticsChart labels={data.labels} datasets={data.datasets} />
        </div>
      )}

      <p className="text-xs text-[#8b949e] mt-4">
        Showing open items per priority across {data.labels.length} scans in the last {validDays} days.
      </p>
    </main>
  );
}
