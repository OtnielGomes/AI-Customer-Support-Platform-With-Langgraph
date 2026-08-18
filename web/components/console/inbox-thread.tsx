"use client";

import { useState, useTransition } from "react";

import { ChatWindow } from "@/components/portal/chat-window";
import { ToolCallsTable } from "@/components/console/tool-calls-table";
import { TraceTimeline } from "@/components/console/trace-timeline";
import { StatusBadge } from "@/components/status-badge";
import type {
  AgentEventResponse,
  AgentRunResponse,
  ChatMessage,
  TicketResponse,
} from "@/lib/api/types";
import { formatDate } from "@/lib/format";
import { takeoverAction } from "@/app/console/actions";

export function InboxThread({
  ticket,
  messages,
  run,
  events,
}: {
  ticket: TicketResponse;
  messages: ChatMessage[];
  run: AgentRunResponse | null;
  events: AgentEventResponse[];
}) {
  const [busy, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(280px,0.8fr)]">
      <ChatWindow ticket={ticket} initialMessages={messages} variant="console" />
      <aside className="grid gap-4">
        <section className="rounded-2xl border border-white/10 p-4 text-sm">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-xs uppercase tracking-wide text-[#9aa3ad]">Cliente</h2>
            <StatusBadge status={ticket.status} />
          </div>
          <p className="mt-2 text-white">{ticket.customer_name}</p>
          <p className="text-[#9aa3ad]">{ticket.customer_email}</p>
          <p className="mt-2 text-xs text-[#9aa3ad]">Aberto {formatDate(ticket.created_at)}</p>
          {ticket.assigned_agent ? (
            <p className="mt-2 text-xs text-amber-200">Assumido por {ticket.assigned_agent}</p>
          ) : null}
          <button
            type="button"
            disabled={busy}
            onClick={() => {
              startTransition(async () => {
                setError(null);
                const result = await takeoverAction(ticket.id);
                if (result?.error) {
                  setError(result.error);
                }
              });
            }}
            className="mt-4 rounded-full bg-white px-4 py-2 text-xs font-medium text-[#12151a] disabled:opacity-60"
          >
            Assumir conversa
          </button>
          {error ? <p className="mt-2 text-xs text-rose-400">{error}</p> : null}
        </section>
        {run ? <TraceTimeline run={run} events={events} /> : null}
        {events.length > 0 ? <ToolCallsTable events={events} /> : null}
      </aside>
    </div>
  );
}
