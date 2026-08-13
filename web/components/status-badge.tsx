import type { TicketStatus } from "@/lib/api/types";
import { statusLabel } from "@/lib/format";

const STYLES: Record<TicketStatus, string> = {
  open: "bg-sky-100 text-sky-900",
  in_progress: "bg-amber-100 text-amber-900",
  resolved: "bg-emerald-100 text-emerald-900",
  escalated: "bg-rose-100 text-rose-900",
  closed: "bg-stone-200 text-stone-700",
};

export function StatusBadge({ status }: { status: TicketStatus | string }) {
  const key = status as TicketStatus;
  const className = STYLES[key] ?? "bg-stone-200 text-stone-700";
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${className}`}
    >
      {statusLabel(status)}
    </span>
  );
}
