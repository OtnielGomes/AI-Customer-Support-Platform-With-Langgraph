"use client";

import { useState } from "react";

import { ToolCallsTable } from "@/components/console/tool-calls-table";
import { TraceTimeline } from "@/components/console/trace-timeline";
import { StatusBadge } from "@/components/status-badge";
import type {
  AgentEventResponse,
  AgentRunResponse,
  TicketResponse,
} from "@/lib/api/types";
import { formatDate } from "@/lib/format";
import { closeTicketAction } from "@/app/console/actions";

type Tab = "conversation" | "trace" | "tools";

export function TicketDetail({
  ticket,
  run,
  events,
}: {
  ticket: TicketResponse;
  run: AgentRunResponse | null;
  events: AgentEventResponse[];
}) {
  const [tab, setTab] = useState<Tab>("conversation");
  const [closeError, setCloseError] = useState<string | null>(null);

  return (
    <div className="grid gap-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-[#9aa3ad]">Ticket</p>
          <h1 className="mt-1 font-[family-name:var(--font-serif)] text-3xl text-white">
            {ticket.subject}
          </h1>
          <p className="mt-2 text-sm text-[#c5cdd6]">
            {ticket.customer_name} · {ticket.customer_email} · {formatDate(ticket.created_at)}
          </p>
        </div>
        <StatusBadge status={ticket.status} />
      </header>
      <div className="flex gap-2">
        {(["conversation", "trace", "tools"] as const).map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => setTab(item)}
            className={`rounded-full px-4 py-1.5 text-sm capitalize ${
              tab === item ? "bg-white text-[#12151a]" : "bg-white/10 text-[#c5cdd6]"
            }`}
          >
            {item === "tools" ? "Tool Calls" : item === "trace" ? "Agent Trace" : "Conversation"}
          </button>
        ))}
      </div>
      {tab === "conversation" ? (
        <section className="grid gap-4 rounded-2xl border border-white/10 p-5 text-sm leading-6">
          <div>
            <h2 className="text-xs uppercase tracking-wide text-[#9aa3ad]">Customer</h2>
            <p className="mt-2 whitespace-pre-wrap text-[#e8e4dc]">{ticket.description}</p>
          </div>
          {ticket.resolution ? (
            <div>
              <h2 className="text-xs uppercase tracking-wide text-[#9aa3ad]">Resolution</h2>
              <p className="mt-2 whitespace-pre-wrap text-[#e8e4dc]">{ticket.resolution}</p>
            </div>
          ) : null}
          {ticket.status !== "closed" ? (
            <form
              className="mt-2 grid gap-2"
              action={async (formData) => {
                setCloseError(null);
                const result = await closeTicketAction(ticket.id, formData);
                if (result?.error) {
                  setCloseError(result.error);
                }
              }}
            >
              <div className="flex gap-2">
                <input
                  name="reason"
                  placeholder="Close reason (optional)"
                  className="flex-1 rounded-lg border border-white/10 bg-[#12151a] px-3 py-2 text-sm"
                />
                <button type="submit" className="rounded-lg bg-white/10 px-4 py-2 text-sm">
                  Close ticket
                </button>
              </div>
              {closeError ? <p className="text-sm text-rose-300">{closeError}</p> : null}
            </form>
          ) : null}
        </section>
      ) : null}
      {tab === "trace" ? <TraceTimeline run={run} events={events} /> : null}
      {tab === "tools" ? <ToolCallsTable events={events} /> : null}
    </div>
  );
}
