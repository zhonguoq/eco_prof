import ReactECharts from "echarts-for-react";
import { useEffect, useRef, useState } from "react";
import {
  fetchYieldCurve,
  fetchYieldCurveInfo,
  YieldCurveSnapshot,
} from "../api/client";

// ---------------------------------------------------------------------------
// Color palette for up to 8 curves
// ---------------------------------------------------------------------------
const PALETTE = [
  "#60a5fa", // blue   — most recent / default first
  "#34d399", // green
  "#f59e0b", // amber
  "#f87171", // red
  "#a78bfa", // purple
  "#fb923c", // orange
  "#38bdf8", // sky
  "#f472b6", // pink
];

function colorFor(index: number) {
  return PALETTE[index % PALETTE.length];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function isoToLabel(date: string) {
  // "2024-04-12" → "2024-04"
  return date.slice(0, 7);
}

function subtractYears(isoDate: string, years: number): string {
  const d = new Date(isoDate);
  d.setFullYear(d.getFullYear() - years);
  return d.toISOString().slice(0, 10);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export default function YieldCurveChart() {
  const [info, setInfo] = useState<{ min_date: string; max_date: string } | null>(null);
  const [selectedDates, setSelectedDates] = useState<string[]>([]);
  const [curves, setCurves] = useState<YieldCurveSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [inputDate, setInputDate] = useState("");
  const prevDatesRef = useRef<string>("");

  // Load info on mount → set default dates
  useEffect(() => {
    fetchYieldCurveInfo()
      .then(inf => {
        setInfo(inf);
        const defaults = [
          inf.max_date,
          subtractYears(inf.max_date, 1),
          subtractYears(inf.max_date, 2),
          subtractYears(inf.max_date, 3),
        ].filter(d => d >= inf.min_date);
        setSelectedDates(defaults);
        setInputDate(inf.max_date);
      })
      .catch(e => setError(String(e)));
  }, []);

  // Fetch curves whenever selectedDates changes
  useEffect(() => {
    if (selectedDates.length === 0) return;
    const key = selectedDates.join(",");
    if (key === prevDatesRef.current) return;
    prevDatesRef.current = key;

    setLoading(true);
    setError(null);
    fetchYieldCurve(selectedDates)
      .then(data => setCurves(data))
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false));
  }, [selectedDates]);

  // All maturity labels (X-axis) — derived from first curve with data
  const maturities = curves.length > 0
    ? curves.reduce((best, c) => c.points.length > best.points.length ? c : best, curves[0]).points.map(p => p.maturity)
    : ["1M","3M","6M","1Y","2Y","3Y","5Y","7Y","10Y","20Y","30Y"];

  // Compute Y-axis bounds from all visible data so the chart fills the space
  const allValues = curves.flatMap(c => c.points.map(p => p.value));
  const dataMin = allValues.length > 0 ? Math.min(...allValues) : 0;
  const dataMax = allValues.length > 0 ? Math.max(...allValues) : 6;
  const range = dataMax - dataMin || 1;
  const yMin = Math.max(0, parseFloat((dataMin - range * 0.15).toFixed(2)));
  const yMax = parseFloat((dataMax + range * 0.1).toFixed(2));

  const echartsOption = {
    backgroundColor: "transparent",
    grid: { top: 44, bottom: 28, left: 54, right: 16 },
    legend: {
      top: 4,
      right: 8,
      textStyle: { color: "#9ca3af", fontSize: 11 },
      itemWidth: 16,
      itemHeight: 2,
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: "#1f2937",
      borderColor: "#374151",
      textStyle: { color: "#f9fafb", fontSize: 12 },
      formatter: (params: { seriesName: string; value: number }[]) =>
        params
          .filter(p => p.value != null)
          .map(p => `<span style="color:${colorFor(curves.findIndex(c => isoToLabel(c.actual_date) === p.seriesName))}">${p.seriesName}</span>: ${p.value.toFixed(2)}%`)
          .join("<br/>"),
    },
    xAxis: {
      type: "category",
      data: maturities,
      axisLine: { lineStyle: { color: "#374151" } },
      axisTick: { show: false },
      axisLabel: { color: "#6b7280", fontSize: 10 },
      boundaryGap: false,
    },
    yAxis: {
      type: "value",
      min: yMin,
      max: yMax,
      name: "Yield %",
      nameTextStyle: { color: "#6b7280", fontSize: 9 },
      axisLabel: { color: "#6b7280", fontSize: 10, formatter: "{value}%" },
      splitLine: { lineStyle: { color: "#1f2937" } },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: curves.map((curve, i) => ({
      name: isoToLabel(curve.actual_date),
      type: "line",
      data: maturities.map(m => {
        const pt = curve.points.find(p => p.maturity === m);
        return pt ? pt.value : null;
      }),
      smooth: false,
      symbol: "circle",
      symbolSize: 5,
      lineStyle: { width: 2, color: colorFor(i) },
      itemStyle: { color: colorFor(i) },
      connectNulls: false,
    })),
  };

  function addDate() {
    const d = inputDate.trim();
    if (!d || selectedDates.includes(d)) return;
    if (info && (d < info.min_date || d > info.max_date)) return;
    setSelectedDates(prev => [...prev, d]);
  }

  function removeDate(d: string) {
    setSelectedDates(prev => prev.filter(x => x !== d));
    setCurves(prev => prev.filter(c => c.requested_date !== d));
  }

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-4 col-span-full">
      <p className="text-xs text-gray-400 font-semibold mb-3 uppercase tracking-wider">
        收益率曲线快照 · Yield Curve Snapshot
      </p>

      {/* Date chips + picker */}
      <div className="flex flex-wrap items-center gap-2 mb-3">
        {selectedDates.map((d, i) => (
          <span
            key={d}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-mono"
            style={{ backgroundColor: colorFor(i) + "22", color: colorFor(i), border: `1px solid ${colorFor(i)}55` }}
          >
            {d}
            <button
              onClick={() => removeDate(d)}
              className="ml-0.5 opacity-60 hover:opacity-100 text-xs leading-none"
              aria-label={`移除 ${d}`}
            >
              ×
            </button>
          </span>
        ))}

        {selectedDates.length < 8 && (
          <div className="flex items-center gap-1 ml-auto">
            <input
              type="date"
              value={inputDate}
              min={info?.min_date}
              max={info?.max_date}
              onChange={e => setInputDate(e.target.value)}
              className="bg-gray-800 border border-gray-700 text-gray-300 text-xs rounded px-2 py-0.5 focus:outline-none focus:border-blue-500"
            />
            <button
              onClick={addDate}
              className="bg-gray-700 hover:bg-gray-600 text-gray-200 text-xs rounded px-2 py-0.5 transition-colors"
            >
              + 添加
            </button>
          </div>
        )}
      </div>

      {/* Chart */}
      {loading ? (
        <div className="animate-pulse bg-gray-800 rounded-lg h-56" />
      ) : error ? (
        <div className="h-56 flex items-center justify-center text-gray-600 text-xs">数据加载失败</div>
      ) : (
        <ReactECharts option={echartsOption} style={{ height: "220px" }} />
      )}

      {/* Inversion annotation */}
      {curves.some(c => {
        const p1m = c.points.find(p => p.maturity === "1M");
        const p10y = c.points.find(p => p.maturity === "10Y");
        return p1m && p10y && p1m.value > p10y.value;
      }) && (
        <p className="text-xs text-red-400 mt-2">
          ⚠ 部分曲线呈倒挂形态（短端 &gt; 长端），参考{" "}
          <a href="#" className="underline opacity-70">收益率曲线概念页</a>
        </p>
      )}
    </div>
  );
}
