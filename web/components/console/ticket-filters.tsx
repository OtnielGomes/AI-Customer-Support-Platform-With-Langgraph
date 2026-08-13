import Link from "next/link";

import type { TicketIntent, TicketStatus } from "@/lib/api/types";

const STATUSES: Array<TicketStatus | ""> = [
  "",
  "open",
  "in_progress",
  "resolved",
  "escalated",
  "closed",
];
const INTENTS: Array<TicketIntent | ""> = ["", "billing", "logistics", "account", "unknown"];

interface TicketFiltersProps {
  status?: string;
  intent?: string;
  q?: string;
}

export function TicketFilters({ status = "", intent = "", q = "" }: TicketFiltersProps) {
  return (
    <form className="flex flex-wrap items-end gap-3" action="/console/tickets">
      <label className="grid gap-1 text-xs text-[#9aa3ad]">
        Search
        <input
          name="q"
          defaultValue={q}
          placeholder="Subject, email, text"
          className="min-w-56 rounded-lg border border-white/10 bg-[#12151a] px-3 py-2 text-sm text-white"
        />
      </label>
      <label className="grid gap-1 text-xs text-[#9aa3ad]">
        Status
        <select
          name="status"
          defaultValue={status}
          className="rounded-lg border border-white/10 bg-[#12151a] px-3 py-2 text-sm text-white"
        >
          {STATUSES.map((value) => (
            <option key={value || "all"} value={value}>
              {value || "All"}
            </option>
          ))}
        </select>
      </label>
      <label className="grid gap-1 text-xs text-[#9aa3ad]">
        Intent
        <select
          name="intent"
          defaultValue={intent}
          className="rounded-lg border border-white/10 bg-[#12151a] px-3 py-2 text-sm text-white"
        >
          {INTENTS.map((value) => (
            <option key={value || "all"} value={value}>
              {value || "All"}
            </option>
          ))}
        </select>
      </label>
      <button
        type="submit"
        className="rounded-lg bg-white/10 px-4 py-2 text-sm text-white hover:bg-white/15"
      >
        Filter
      </button>
      <Link href="/console/tickets" className="px-2 py-2 text-sm text-[#9aa3ad] hover:text-white">
        Reset
      </Link>
    </form>
  );
}
