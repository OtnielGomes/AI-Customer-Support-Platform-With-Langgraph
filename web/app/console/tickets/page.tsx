import Link from "next/link";

import { TicketFilters } from "@/components/console/ticket-filters";
import { TicketTable } from "@/components/console/ticket-table";
import { listTickets } from "@/lib/api/server";

export default async function ConsoleTicketsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const query = new URLSearchParams();
  const status = first(params.status);
  const intent = first(params.intent);
  const q = first(params.q);
  const offset = first(params.offset) ?? "0";
  if (status) query.set("status", status);
  if (intent) query.set("intent", intent);
  if (q) query.set("q", q);
  query.set("limit", "20");
  query.set("offset", offset);

  const list = await listTickets(query);
  const nextOffset = list.offset + list.limit;
  const prevOffset = Math.max(0, list.offset - list.limit);

  return (
    <div className="grid gap-6">
      <header>
        <h1 className="font-[family-name:var(--font-serif)] text-3xl text-white">Tickets</h1>
        <p className="mt-1 text-sm text-[#9aa3ad]">{list.total} in the workspace</p>
      </header>
      <TicketFilters status={status} intent={intent} q={q} />
      <TicketTable tickets={list.items} />
      <div className="flex gap-3 text-sm">
        {list.offset > 0 ? (
          <Link
            href={`/console/tickets?${withOffset(query, prevOffset)}`}
            className="text-[#9aa3ad] hover:text-white"
          >
            Previous
          </Link>
        ) : null}
        {nextOffset < list.total ? (
          <Link
            href={`/console/tickets?${withOffset(query, nextOffset)}`}
            className="text-[#9aa3ad] hover:text-white"
          >
            Next
          </Link>
        ) : null}
      </div>
    </div>
  );
}

function first(value: string | string[] | undefined): string | undefined {
  if (Array.isArray(value)) {
    return value[0];
  }
  return value;
}

function withOffset(query: URLSearchParams, offset: number): string {
  const next = new URLSearchParams(query);
  next.set("offset", String(offset));
  return next.toString();
}
