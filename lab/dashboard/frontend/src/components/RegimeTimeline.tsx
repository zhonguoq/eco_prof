import { useEffect, useState } from "react";
import { fetchDiagnosisHistory, HistoryRecord } from "../api/client";

const regimeColors: Record<string, string> = {
  Goldilocks:  "bg-emerald-500",
  Overheating: "bg-orange-500",
  Stagflation: "bg-red-500",
  Deflation:   "bg-blue-500",
};

const regimeDotBorder: Record<string, string> = {
  Goldilocks:  "ring-emerald-500/30",
  Overheating: "ring-orange-500/30",
  Stagflation: "ring-red-500/30",
  Deflation:   "ring-blue-500/30",
};

export default function RegimeTimeline() {
  const [history, setHistory] = useState<HistoryRecord[]>([]);

  useEffect(() => {
    fetchDiagnosisHistory(90).then(setHistory).catch(console.error);
  }, []);

  if (history.length === 0) {
    return (
      <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-5">
        <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">
          Regime 变迁时间线
        </h2>
        <p className="text-xs text-gray-600">暂无历史记录。数据将在每日自动更新后积累。</p>
      </div>
    );
  }

  // Show records chronologically (oldest first)
  const sorted = [...history].reverse();

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-5">
      <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-4">
        Regime 变迁时间线
      </h2>
      <div className="relative">
        {/* Timeline line */}
        <div className="absolute left-3 top-2 bottom-2 w-px bg-gray-800" />

        <div className="space-y-3">
          {sorted.map((r, i) => {
            const color = regimeColors[r.regime_quadrant] || "bg-gray-500";
            const ring = regimeDotBorder[r.regime_quadrant] || "ring-gray-500/30";
            const isLast = i === sorted.length - 1;

            return (
              <div key={r.date} className="flex items-start gap-3 pl-0.5">
                {/* Dot */}
                <div className={`mt-1 w-5 h-5 rounded-full ${color} ring-4 ${ring} flex-shrink-0 z-10 ${isLast ? "scale-110" : "scale-75 opacity-70"}`} />
                {/* Content */}
                <div className={`flex-1 ${isLast ? "" : "opacity-70"}`}>
                  <div className="flex items-baseline gap-2">
                    <span className="text-xs font-mono text-gray-500">{r.date}</span>
                    <span className="text-xs font-semibold text-white">
                      {r.regime_quadrant_cn || r.regime_quadrant}
                    </span>
                  </div>
                  <div className="text-[10px] text-gray-600 mt-0.5">
                    {r.debt_cycle_stage}
                    {r.growth_value != null && ` · GDP ${r.growth_value.toFixed(1)}%`}
                    {r.inflation_value != null && ` · CPI ${r.inflation_value.toFixed(1)}%`}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
