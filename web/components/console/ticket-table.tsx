import Link from "next/link";

import { StatusBadge } from "@/components/status-badge";
import type { TicketSummary } from "@/lib/api/types";
import { formatDate } from "@/lib/format";

export function TicketTable({ tickets }: { tickets: TicketSummary[] }) {
  if (tickets.length === 0) {
    return <p className="text-sm text-[#9aa3ad]">No tickets match these filters.</p>;
  }

  return (
    <div className="overflow-x-auto rounded-2xl border border-white/10">
      <table className="w-full min-w-[720px] text-left text-sm">
        <thead className="bg-white/5 text-xs uppercase tracking-wide text-[#9aa3ad]">
          <tr>
            <th className="px-4 py-3 font-medium">Subject</th>
            <th className="px-4 py-3 font-medium">Customer</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Intent</th>
            <th className="px-4 py-3 font-medium">Opened</th>
          </tr>
        </thead>
        <tbody>
          {tickets.map((ticket) => (
            <tr key={ticket.id} className="border-t border-white/10">
              <td className="px-4 py-3">
                <Link
                  href={`/console/tickets/${ticket.id}`}
                  className="font-medium text-white hover:underline"
                >
                  {ticket.subject}
                </Link>
              </td>
              <td className="px-4 py-3 text-[#c5cdd6]">
                {ticket.customer_name ?? "—"}
                <div className="text-xs text-[#9aa3ad]">{ticket.customer_email}</div>
              </td>
              <td className="px-4 py-3">
                <StatusBadge status={ticket.status} />
              </td>
              <td className="px-4 py-3 capitalize text-[#c5cdd6]">{ticket.intent ?? "—"}</td>
              <td className="px-4 py-3 text-[#9aa3ad]">{formatDate(ticket.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
