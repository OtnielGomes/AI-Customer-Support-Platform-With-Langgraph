import type { AnalyticsOverviewResponse, ToolAnalyticsItem } from "@/lib/api/types";
import { formatMs, formatPercent } from "@/lib/format";

export function AnalyticsDashboard({
  overview,
  tools,
}: {
  overview: AnalyticsOverviewResponse;
  tools: ToolAnalyticsItem[];
}) {
  const maxVolume = Math.max(1, ...overview.volume_by_day.map((point) => point.count));
  const maxCalls = Math.max(1, ...tools.map((item) => item.calls));

  return (
    <div className="grid gap-8">
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card label="Tickets" value={String(overview.total_tickets)} />
        <Card label="Escalation rate" value={formatPercent(overview.escalation_rate)} />
        <Card
          label="Avg confidence"
          value={overview.avg_confidence == null ? "—" : overview.avg_confidence.toFixed(2)}
        />
        <Card label="Avg run latency" value={formatMs(overview.avg_resolution_ms)} />
      </section>
      <section className="grid gap-6 lg:grid-cols-2">
        <article className="rounded-2xl border border-white/10 p-5">
          <h2 className="mb-4 text-sm font-medium text-white">Status mix</h2>
          <BarList items={Object.entries(overview.by_status)} />
        </article>
        <article className="rounded-2xl border border-white/10 p-5">
          <h2 className="mb-4 text-sm font-medium text-white">Intent mix</h2>
          <BarList items={Object.entries(overview.by_intent)} />
        </article>
      </section>
      <article className="rounded-2xl border border-white/10 p-5">
        <h2 className="mb-4 text-sm font-medium text-white">Volume by day</h2>
        <div className="flex h-40 items-end gap-1">
          {overview.volume_by_day.length === 0 ? (
            <p className="text-sm text-[#9aa3ad]">No volume yet.</p>
          ) : (
            overview.volume_by_day.map((point) => (
              <div key={point.date} className="flex flex-1 flex-col items-center gap-1">
                <div
                  className="w-full rounded-t bg-[#3d8bfd]"
                  style={{ height: `${(point.count / maxVolume) * 100}%` }}
                  title={`${point.date}: ${point.count}`}
                />
              </div>
            ))
          )}
        </div>
      </article>
      <article className="rounded-2xl border border-white/10 p-5">
        <h2 className="mb-4 text-sm font-medium text-white">Tool calls</h2>
        {tools.length === 0 ? (
          <p className="text-sm text-[#9aa3ad]">No tool events recorded yet.</p>
        ) : (
          <div className="grid gap-3">
            {tools.map((item) => (
              <div key={item.name}>
                <div className="mb-1 flex justify-between text-sm">
                  <span>{item.name}</span>
                  <span className="text-[#9aa3ad]">
                    {item.calls} calls · {formatPercent(item.error_rate)} errors ·{" "}
                    {formatMs(item.p95_latency_ms)} p95
                  </span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-white/10">
                  <div
                    className="h-full bg-[#c45c26]"
                    style={{ width: `${(item.calls / maxCalls) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </article>
    </div>
  );
}

function Card({ label, value }: { label: string; value: string }) {
  return (
    <article className="rounded-2xl border border-white/10 p-5">
      <p className="text-xs uppercase tracking-wide text-[#9aa3ad]">{label}</p>
      <p className="mt-2 font-[family-name:var(--font-serif)] text-3xl text-white">{value}</p>
    </article>
  );
}

function BarList({ items }: { items: Array<[string, number]> }) {
  const max = Math.max(1, ...items.map(([, count]) => count));
  return (
    <div className="grid gap-2">
      {items.map(([name, count]) => (
        <div key={name} className="grid grid-cols-[7rem_1fr_2rem] items-center gap-2 text-sm">
          <span className="capitalize text-[#c5cdd6]">{name.replaceAll("_", " ")}</span>
          <div className="h-2 overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full bg-[#3d8bfd]"
              style={{ width: `${(count / max) * 100}%` }}
            />
          </div>
          <span className="text-right text-[#9aa3ad]">{count}</span>
        </div>
      ))}
    </div>
  );
}
