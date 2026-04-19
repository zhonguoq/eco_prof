import { useEffect, useState } from "react";
import { fetchRegime, RegimeResponse } from "../api/client";
import StatusBadge from "./StatusBadge";

const quadrantColors: Record<string, string> = {
  Goldilocks:  "border-emerald-500 bg-emerald-950/60 text-emerald-300",
  Overheating: "border-orange-500  bg-orange-950/60  text-orange-300",
  Stagflation: "border-red-500     bg-red-950/60     text-red-300",
  Deflation:   "border-blue-500    bg-blue-950/60    text-blue-300",
};

const quadrantDim: Record<string, string> = {
  Goldilocks:  "border-gray-700 bg-gray-900/30 text-gray-600",
  Overheating: "border-gray-700 bg-gray-900/30 text-gray-600",
  Stagflation: "border-gray-700 bg-gray-900/30 text-gray-600",
  Deflation:   "border-gray-700 bg-gray-900/30 text-gray-600",
};

const QUADRANT_GRID = [
  ["Goldilocks", "Overheating"],
  ["Deflation",  "Stagflation"],
] as const;

const QUADRANT_LABELS: Record<string, string> = {
  Goldilocks:  "Goldilocks\n高增长 低通胀",
  Overheating: "Overheating\n高增长 高通胀",
  Deflation:   "Deflation\n低增长 低通胀",
  Stagflation: "Stagflation\n低增长 高通胀",
};

function TiltBar({ label, tilt }: { label: string; tilt: number }) {
  // tilt: -2 to +2, map to visual bar
  const absVal = Math.abs(tilt);
  const isPositive = tilt > 0;
  const color = isPositive ? "bg-emerald-500" : "bg-red-500";
  const symbol = tilt > 0 ? "+".repeat(tilt) : "−".repeat(-tilt);

  return (
    <div className="flex items-center gap-2 py-1">
      <span className="text-xs text-gray-400 w-20 text-right">{label}</span>
      <div className="flex-1 flex items-center gap-1">
        <div className="w-24 h-2 bg-gray-800 rounded-full overflow-hidden relative">
          <div
            className={`h-full rounded-full ${color} transition-all`}
            style={{ width: `${absVal * 25}%`, marginLeft: isPositive ? "50%" : `${50 - absVal * 25}%` }}
          />
          <div className="absolute top-0 left-1/2 w-px h-full bg-gray-600" />
        </div>
        <span className={`text-xs font-mono w-6 ${isPositive ? "text-emerald-400" : "text-red-400"}`}>
          {symbol}
        </span>
      </div>
    </div>
  );
}

export default function RegimePanel() {
  const [data, setData] = useState<RegimeResponse | null>(null);

  useEffect(() => {
    fetchRegime().then(setData).catch(console.error);
  }, []);

  if (!data) return <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-5 animate-pulse h-64" />;

  const current = data.quadrant;

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-5">
      <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-4">
        增长-通胀 Regime 判断
      </h2>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 4-Quadrant Grid */}
        <div>
          <div className="grid grid-cols-2 gap-1.5">
            {QUADRANT_GRID.flat().map(q => (
              <div
                key={q}
                className={`rounded-lg border p-3 text-center text-xs font-medium transition-all ${
                  q === current ? quadrantColors[q] : quadrantDim[q]
                }`}
              >
                {QUADRANT_LABELS[q].split("\n").map((line, i) => (
                  <div key={i} className={i === 0 ? "font-semibold text-sm" : "mt-0.5 opacity-80"}>
                    {line}
                  </div>
                ))}
              </div>
            ))}
          </div>
          {/* Axis labels */}
          <div className="flex justify-between mt-2 text-[10px] text-gray-600 px-1">
            <span>← 低通胀</span>
            <span>高通胀 →</span>
          </div>
          <div className="mt-2 text-center">
            <span className="text-xs text-gray-500">
              实际GDP {data.growth.value?.toFixed(1)}% | CPI {data.inflation.value?.toFixed(1)}%
            </span>
          </div>
        </div>

        {/* Asset Tilts */}
        <div>
          <h3 className="text-xs text-gray-500 mb-2">资产配置倾向</h3>
          {data.asset_tilts ? (
            data.asset_tilts.map(t => (
              <TiltBar key={t.asset} label={t.asset_cn} tilt={t.tilt} />
            ))
          ) : (
            <p className="text-xs text-gray-600">数据不足</p>
          )}
          <p className="text-[10px] text-gray-600 mt-2">
            基于 Dalio 全天候框架的 regime 映射
          </p>
        </div>

        {/* Long-term Risk + Aux Signals */}
        <div>
          <h3 className="text-xs text-gray-500 mb-2">长期结构性风险</h3>
          {Object.entries(data.long_term).map(([key, item]) => (
            <div key={key} className="flex items-start gap-2 py-1.5 border-b border-gray-800 last:border-0">
              {item.status && <StatusBadge status={item.status as "ok" | "warning" | "danger"} />}
              <span className="text-xs text-gray-400">{item.note}</span>
            </div>
          ))}

          <h3 className="text-xs text-gray-500 mt-4 mb-2">辅助信号</h3>
          {data.aux_signals.map(s => (
            <div key={s.id} className="flex items-center gap-2 py-1 border-b border-gray-800 last:border-0">
              <StatusBadge status={s.status === "neutral" ? "ok" : s.status} />
              <span className="text-xs text-gray-400">{s.label}</span>
              <span className="text-xs text-white font-mono ml-auto">{s.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
