"use client";

import useSWR from "swr";

import { clientFetcher } from "@/lib/api/client";
import type { TicketListResponse } from "@/lib/api/types";
import { formatDate } from "@/lib/format";
import { StatusBadge } from "@/components/status-badge";
import { replyEscalationAction } from "@/app/console/actions";

export function EscalationQueue() {
  const { data, error, isLoading } = useSWR<TicketListResponse>(
    "/escalations?limit=50",
    clientFetcher,
    { refreshInterval: 8000 },
  );

  if (isLoading) {
    return <p className="text-sm text-[#9aa3ad]">Loading queue…</p>;
  }
  if (error) {
    return <p className="text-sm text-rose-300">Could not load escalations.</p>;
  }
  const items = data?.items ?? [];
  if (items.length === 0) {
    return <p className="text-sm text-[#9aa3ad]">The human queue is empty.</p>;
  }

  return (
    <div className="grid gap-6">
      {items.map((ticket) => (
        <article key={ticket.id} className="rounded-2xl border border-white/10 p-5">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-medium text-white">{ticket.subject}</h2>
              <p className="text-sm text-[#9aa3ad]">
                {ticket.customer_name} · waiting since {formatDate(ticket.escalated_at)}
              </p>
            </div>
            <StatusBadge status={ticket.status} />
          </div>
          <form action={replyEscalationAction.bind(null, ticket.id)} className="grid gap-3">
            <textarea
              name="answer"
              required
              rows={4}
              placeholder="Write the customer-facing reply…"
              className="rounded-lg border border-white/10 bg-[#12151a] px-3 py-2 text-sm"
            />
            <button
              type="submit"
              className="justify-self-start rounded-full bg-white px-4 py-2 text-sm font-medium text-[#12151a]"
            >
              Send reply and resume graph
            </button>
          </form>
        </article>
      ))}
    </div>
  );
}
