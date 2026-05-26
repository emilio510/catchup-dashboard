"use client";

import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import { Line } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

interface AnalyticsChartProps {
  labels: string[];
  datasets: {
    P0: number[];
    P1: number[];
    P2: number[];
    P3: number[];
  };
}

// Color literals corresponding to design tokens.
// Chart.js cannot read CSS variables directly, so we use fixed hex/rgba values.
// --color-risk       → #ff453a   (P0)
// --color-warn       → #ff9f0a   (P1)
// --color-ok         → #30d158   (P2)
// neutral            → rgba(255,255,255,0.45)  (P3)
// --color-border-subtle   → rgba(255,255,255,0.06)  (grid lines)
// --color-text-ghost      → rgba(255,255,255,0.35)  (tick labels)
// --color-text            → #f5f5f7  (tooltip text)
// --color-border-strong   → rgba(255,255,255,0.14)  (tooltip border)
// --color-text-dim        → rgba(255,255,255,0.60)  (legend labels)
const COLORS = {
  P0: "#ff453a",
  P1: "#ff9f0a",
  P2: "#30d158",
  P3: "rgba(255, 255, 255, 0.45)",
};

export function AnalyticsChart({ labels, datasets }: AnalyticsChartProps) {
  const data = {
    labels,
    datasets: [
      {
        label: "P0 - Respond Today",
        data: datasets.P0,
        borderColor: COLORS.P0,
        backgroundColor: COLORS.P0,
        tension: 0.3,
        pointRadius: 3,
      },
      {
        label: "P1 - This Week",
        data: datasets.P1,
        borderColor: COLORS.P1,
        backgroundColor: COLORS.P1,
        tension: 0.3,
        pointRadius: 3,
      },
      {
        label: "P2 - Respond",
        data: datasets.P2,
        borderColor: COLORS.P2,
        backgroundColor: COLORS.P2,
        tension: 0.3,
        pointRadius: 3,
      },
      {
        label: "P3 - Monitor",
        data: datasets.P3,
        borderColor: COLORS.P3,
        backgroundColor: COLORS.P3,
        tension: 0.3,
        pointRadius: 3,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: "top" as const,
        labels: {
          color: "rgba(255, 255, 255, 0.60)", // --color-text-dim
          usePointStyle: true,
        },
      },
      tooltip: {
        mode: "index" as const,
        intersect: false,
        backgroundColor: "rgba(10, 10, 12, 0.95)", // glass surface over --color-bg
        borderColor: "rgba(255, 255, 255, 0.14)",   // --color-border-strong
        borderWidth: 1,
        titleColor: "#f5f5f7", // --color-text
        bodyColor: "#f5f5f7",  // --color-text
      },
    },
    scales: {
      x: {
        ticks: {
          color: "rgba(255, 255, 255, 0.35)", // --color-text-ghost
          maxTicksLimit: 12,
          font: { family: "'JetBrains Mono', ui-monospace, monospace" },
        },
        grid: { color: "rgba(255, 255, 255, 0.06)" }, // --color-border-subtle
      },
      y: {
        beginAtZero: true,
        ticks: {
          color: "rgba(255, 255, 255, 0.35)", // --color-text-ghost
          stepSize: 1,
          font: { family: "'JetBrains Mono', ui-monospace, monospace" },
        },
        grid: { color: "rgba(255, 255, 255, 0.06)" }, // --color-border-subtle
      },
    },
  };

  return (
    <div className="h-[400px]">
      <Line data={data} options={options} />
    </div>
  );
}
