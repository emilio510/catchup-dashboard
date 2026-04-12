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
  P0: "#f85149",
  P1: "#d29922",
  P2: "#3fb950",
  P3: "#8b949e",
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
          color: "#e6edf3",
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
        ticks: { color: "#8b949e", maxTicksLimit: 12 },
        grid: { color: "#21262d" },
      },
      y: {
        beginAtZero: true,
        ticks: { color: "#8b949e", stepSize: 1 },
        grid: { color: "#21262d" },
      },
    },
  };

  return (
    <div className="h-[400px]">
      <Line data={data} options={options} />
    </div>
  );
}
