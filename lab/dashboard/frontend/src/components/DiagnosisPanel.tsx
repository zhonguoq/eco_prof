import { useEffect, useState } from "react";
import { fetchDiagnosis, DiagnosisResponse, Signal } from "../api/client";
import StatusBadge from "./StatusBadge";

const stageBg: Record<string, string> = {
  ok:      "border-emerald-700 bg-emerald-950/40",
  warning: "border-amber-700  bg-amber-950/40",
  danger:  "border-red-700    bg-red-950/40",
};

function SignalRow({ s }: { s: Signal }) {
  return (
    <div className="flex items-start gap-3 py-2 border-b border-gray-800 last:border-0">
      <StatusBadge status={s.status} />
      <div className="flex-1 min-w-0">
        <span className="text-gray-300 font-medium">{s.label}</span>
        <span className="text-gray-500 mx-2">·</span>
        <span className="text-white font-mono">{s.value}</span>
        <p className="text-gray-500 text-xs mt-0.5">{s.note}</p>
      </div>
    </div>
  );
}

export default function DiagnosisPanel() {
  const [data, setData] = useState<DiagnosisResponse | null>(null);

  useEffect(() => { fetchDiagnosis().then(setData).catch(console.error); }, []);

  if (!data) return <div className="rounded-xl border border-gray-800 bg-gray-900/50 p-5 animate-pulse h-48" />;

  return (
    <div className={`rounded-xl border p-5 ${stageBg[data.stage_color]}`}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest">周期阶段诊断</h2>
        <div className="flex items-center gap-2">
          <StatusBadge status={data.stage_color} />
          <span className="text-white font-semibold">{data.stage}</span>
        </div>
      </div>
      <div>{data.signals.map(s => <SignalRow key={s.id} s={s} />)}</div>
    </div>
  );
}
