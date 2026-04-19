import ReactECharts from "echarts-for-react";
import { useEffect, useState } from "react";
import { fetchSeries, SeriesPoint } from "../api/client";

interface Props {
  seriesId: string;
  title: string;
  unit?: string;
  years?: number;
  threshold?: number;
  thresholdLabel?: string;
  color?: string;
}

export default function LineChart({
  seriesId, title, unit = "", years = 20,
  threshold, thresholdLabel, color = "#60a5fa",
}: Props) {
  const [data, setData] = useState<SeriesPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchSeries(seriesId, years)
      .then(r => setData(r.data))
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false));
  }, [seriesId, years]);

  if (loading) return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-4 animate-pulse h-56" />
  );
  if (error) return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-4 h-56 flex items-center justify-center text-gray-600 text-xs">
      数据加载失败: {seriesId}
    </div>
  );

  const dates  = data.map(d => d.date);
  const values = data.map(d => d.value);
  const hasThreshold = threshold !== undefined && !isNaN(threshold);

  // Find date ranges where value crosses below threshold (for markArea)
  const dangerRanges: [string, string][] = [];
  if (hasThreshold) {
    let start: string | null = null;
    for (let i = 0; i < dates.length; i++) {
      const below = values[i] < threshold!;
      if (below && start === null) start = dates[i];
      if (!below && start !== null) {
        dangerRanges.push([start, dates[i - 1]]);
        start = null;
      }
    }
    if (start !== null) dangerRanges.push([start, dates[dates.length - 1]]);
  }

  const option = {
    backgroundColor: "transparent",
    grid: { top: 36, bottom: 28, left: 54, right: 16 },
    tooltip: {
      trigger: "axis",
      backgroundColor: "#1f2937",
      borderColor: "#374151",
      textStyle: { color: "#f9fafb", fontSize: 12 },
      formatter: (params: { axisValue: string; value: number }[]) => {
        if (!params || !params[0]) return "";
        const p = params[0];
        return `<span style="color:#9ca3af">${p.axisValue}</span><br/><b>${p.value}${unit}</b>`;
      },
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
    series: [
      {
        type: "line",
        data: values,
        smooth: false,
        symbol: "none",
        lineStyle: { width: 1.5, color },
        areaStyle: {
          color: {
            type: "linear", x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: color + "28" },
              { offset: 1, color: color + "04" },
            ],
          },
        },
        ...(hasThreshold ? {
          markLine: {
            silent: true,
            symbol: "none",
            lineStyle: { color: "#ef444480", type: "dashed", width: 1 },
            label: {
              show: true,
              position: "insideEndTop",
              color: "#ef4444",
              fontSize: 10,
              formatter: thresholdLabel ?? String(threshold),
            },
            data: [{ yAxis: threshold }],
          },
          markArea: dangerRanges.length > 0 ? {
            silent: true,
            itemStyle: { color: "#ef444412" },
            data: dangerRanges.map(([s, e]) => [{ xAxis: s }, { xAxis: e }]),
          } : undefined,
        } : {}),
      },
    ],
  };

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-4">
      <p className="text-xs text-gray-400 font-semibold mb-1 uppercase tracking-wider">{title}</p>
      <ReactECharts option={option} style={{ height: "180px" }} />
    </div>
  );
}
