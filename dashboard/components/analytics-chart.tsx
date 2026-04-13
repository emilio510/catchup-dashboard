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

const COLORS = {
  P0: "#f87171",
  P1: "#fbbf24",
  P2: "#4ade80",
  P3: "#94a3b8",
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
          color: "#e2e8f0",
          usePointStyle: true,
        },
      },
      tooltip: {
        mode: "index" as const,
        intersect: false,
      },
    },
    scales: {
      x: {
        ticks: { color: "#64748b", maxTicksLimit: 12 },
        grid: { color: "#162038" },
      },
      y: {
        beginAtZero: true,
        ticks: { color: "#64748b", stepSize: 1 },
        grid: { color: "#162038" },
      },
    },
  };

  return (
    <div className="h-[400px]">
      <Line data={data} options={options} />
    </div>
  );
}
