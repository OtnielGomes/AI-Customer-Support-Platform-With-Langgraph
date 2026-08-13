import type { AgentEventResponse, AgentRunResponse } from "@/lib/api/types";
import { formatDate, formatMs } from "@/lib/format";

export function TraceTimeline({
  run,
  events,
}: {
  run: AgentRunResponse | null;
  events: AgentEventResponse[];
}) {
  if (!run) {
    return <p className="text-sm text-[#9aa3ad]">No agent runs recorded for this ticket yet.</p>;
  }

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap gap-4 text-sm text-[#c5cdd6]">
        <span>Run {run.id.slice(0, 8)}</span>
        <span className="capitalize">{run.status.replaceAll("_", " ")}</span>
        <span>{formatMs(run.total_latency_ms)}</span>
        <span>{formatDate(run.created_at)}</span>
      </div>
      <ol className="grid gap-3 border-l border-white/10 pl-4">
        {events.map((event) => (
          <li key={event.id} className="relative">
            <span className="absolute -left-[21px] mt-1.5 h-2.5 w-2.5 rounded-full bg-[#3d8bfd]" />
            <div className="flex flex-wrap items-baseline gap-2">
              <strong className="text-sm text-white">{event.name}</strong>
              <span className="text-xs uppercase tracking-wide text-[#9aa3ad]">
                {event.event_type}
              </span>
              <span className="text-xs text-[#9aa3ad]">{formatMs(event.latency_ms)}</span>
            </div>
            {event.error ? <p className="text-sm text-rose-300">{event.error}</p> : null}
          </li>
        ))}
      </ol>
    </div>
  );
}
