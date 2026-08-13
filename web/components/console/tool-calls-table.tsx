"use client";

import dynamic from "next/dynamic";

import type { AgentEventResponse } from "@/lib/api/types";
import { formatMs } from "@/lib/format";

const JsonViewer = dynamic(
  () => import("@/components/console/json-viewer").then((mod) => mod.JsonViewer),
  { ssr: false },
);

export function ToolCallsTable({ events }: { events: AgentEventResponse[] }) {
  const tools = events.filter((event) => event.event_type === "tool");
  if (tools.length === 0) {
    return <p className="text-sm text-[#9aa3ad]">No tool calls in this run.</p>;
  }

  return (
    <div className="grid gap-4">
      {tools.map((event) => (
        <article key={event.id} className="rounded-xl border border-white/10 p-4">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <h3 className="font-medium text-white">{event.name}</h3>
            <span className="text-xs text-[#9aa3ad]">{formatMs(event.latency_ms)}</span>
          </div>
          {event.error ? <p className="mb-2 text-sm text-rose-300">{event.error}</p> : null}
          <JsonViewer value={{ input: event.input, output: event.output }} />
        </article>
      ))}
    </div>
  );
}
