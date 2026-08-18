"use client";

import Link from "next/link";
import useSWR from "swr";

import { StatusBadge } from "@/components/status-badge";
import { clientFetcher } from "@/lib/api/client";
import type { TicketListResponse } from "@/lib/api/types";
import { formatDate } from "@/lib/format";

export function InboxList({ status }: { status?: string }) {
  const path = status
    ? `/tickets?status=${status}&sort=last_message_at&limit=50`
    : "/tickets?sort=last_message_at&limit=50";
  const { data, error, isLoading } = useSWR<TicketListResponse>(path, clientFetcher, {
    refreshInterval: 5000,
  });

  if (isLoading) {
    return <p className="text-sm text-[#9aa3ad]">Carregando conversas…</p>;
  }
  if (error) {
    return <p className="text-sm text-rose-400">{String(error)}</p>;
  }
  const items = data?.items ?? [];
  if (items.length === 0) {
    return <p className="text-sm text-[#9aa3ad]">Nenhuma conversa no momento.</p>;
  }

  return (
    <div className="grid gap-2">
      {items.map((ticket) => (
        <Link
          key={ticket.id}
          href={`/console/inbox/${ticket.id}`}
          className="flex items-center justify-between gap-4 rounded-xl border border-white/10 px-4 py-3 hover:bg-white/5"
        >
          <div className="min-w-0">
            <p className="truncate font-medium text-white">{ticket.subject}</p>
            <p className="truncate text-xs text-[#9aa3ad]">
              {ticket.customer_name} · {ticket.customer_email}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            {ticket.status === "escalated" ? (
              <span className="rounded-full bg-amber-400/20 px-2 py-0.5 text-[11px] text-amber-200">
                Aguardando humano
              </span>
            ) : null}
            <StatusBadge status={ticket.status} />
            <span className="text-xs text-[#9aa3ad]">
              {formatDate(ticket.last_message_at ?? ticket.updated_at)}
            </span>
          </div>
        </Link>
      ))}
    </div>
  );
}
