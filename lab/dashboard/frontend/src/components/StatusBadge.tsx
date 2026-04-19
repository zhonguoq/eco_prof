type Status = "ok" | "warning" | "danger";

const colors: Record<Status, string> = {
  ok:      "bg-emerald-900/60 text-emerald-300 border border-emerald-700",
  warning: "bg-amber-900/60  text-amber-300  border border-amber-700",
  danger:  "bg-red-900/60    text-red-300    border border-red-700",
};
const dots: Record<Status, string> = {
  ok: "bg-emerald-400", warning: "bg-amber-400", danger: "bg-red-400",
};
const labels: Record<Status, string> = { ok: "健康", warning: "注意", danger: "危险" };

export default function StatusBadge({ status }: { status: Status }) {
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium ${colors[status]}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dots[status]}`} />
      {labels[status]}
    </span>
  );
}
