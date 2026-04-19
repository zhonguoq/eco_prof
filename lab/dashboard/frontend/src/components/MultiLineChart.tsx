import ReactECharts from "echarts-for-react";
import { useEffect, useState } from "react";
import { fetchSeries, SeriesPoint } from "../api/client";

interface SeriesDef { id: string; label: string; color: string; }
interface Props { title: string; series: SeriesDef[]; unit?: string; years?: number; }

export default function MultiLineChart({ title, series, unit = "%", years = 20 }: Props) {
  const [allData, setAllData] = useState<Record<string, SeriesPoint[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all(
      series.map(s => fetchSeries(s.id, years).then(r => ({ id: s.id, data: r.data })))
    )
      .then(results => {
        const m: Record<string, SeriesPoint[]> = {};
        results.forEach(r => (m[r.id] = r.data));
        setAllData(m);
      })
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false));
  }, [years]); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-4 animate-pulse h-56" />
  );
  if (error) return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-4 h-56 flex items-center justify-center text-gray-600 text-xs">
      数据加载失败
    </div>
  );

  const firstId = series[0]?.id;
  const dates = firstId && allData[firstId] ? allData[firstId].map(d => d.date) : [];

  const option = {
    backgroundColor: "transparent",
    grid: { top: 40, bottom: 28, left: 54, right: 16 },
    legend: {
      top: 4,
      right: 8,
      textStyle: { color: "#9ca3af", fontSize: 11 },
      itemWidth: 14,
      itemHeight: 2,
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: "#1f2937",
      borderColor: "#374151",
      textStyle: { color: "#f9fafb", fontSize: 12 },
    },
    xAxis: {
      type: "category",
      data: dates,
      boundaryGap: false,
      axisLine: { lineStyle: { color: "#374151" } },
      axisTick: { show: false },
      axisLabel: {
        color: "#6b7280",
        fontSize: 10,
        interval: dates.length > 0 ? Math.max(0, Math.floor(dates.length / 6)) : "auto",
        formatter: (v: string) => v.slice(0, 7),
      },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#6b7280", fontSize: 10, formatter: `{value}${unit}` },
      splitLine: { lineStyle: { color: "#1f2937" } },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: series.map(s => ({
      name: s.label,
      type: "line",
      data: (allData[s.id] ?? []).map(d => d.value),
      smooth: false,
      symbol: "none",
      lineStyle: { width: 1.5, color: s.color },
    })),
  };

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-4">
      <p className="text-xs text-gray-400 font-semibold mb-1 uppercase tracking-wider">{title}</p>
      <ReactECharts option={option} style={{ height: "180px" }} />
    </div>
  );
}
