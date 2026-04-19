interface Props {
  label: string;
  value: string | number;
  unit?: string;
  date?: string;
  status?: "ok" | "warning" | "danger" | "neutral";
}

const border: Record<string, string> = {
  ok: "border-l-emerald-500", warning: "border-l-amber-500",
  danger: "border-l-red-500", neutral: "border-l-gray-600",
};
const valueColor: Record<string, string> = {
  ok: "text-emerald-300", warning: "text-amber-300",
  danger: "text-red-300", neutral: "text-white",
};

export default function KpiCard({ label, value, unit = "", date, status = "neutral" }: Props) {
  return (
    <div className={`rounded-lg border border-gray-800 border-l-2 ${border[status]} bg-gray-900/60 px-4 py-3`}>
      <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-xl font-semibold tabular-nums ${valueColor[status]}`}>
        {value}<span className="text-sm ml-1 text-gray-400">{unit}</span>
      </p>
      {date && <p className="text-xs text-gray-600 mt-1">{date}</p>}
    </div>
  );
}
