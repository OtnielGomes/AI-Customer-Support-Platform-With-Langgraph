"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import type { TicketResponse } from "@/lib/api/types";
import { StatusBadge } from "@/components/status-badge";

interface TicketChatProps {
  ticket: TicketResponse;
}

export function TicketChat({ ticket }: TicketChatProps) {
  const router = useRouter();
  const [message, setMessage] = useState(ticket.description);
  const [log, setLog] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(content: string) {
    setBusy(true);
    setError(null);
    setLog((current) => [...current, `You: ${content}`]);
    try {
      const response = await fetch(`/api/support/tickets/${ticket.id}/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [{ role: "user", content }],
        }),
      });
      if (!response.ok || !response.body) {
        throw new Error((await response.text()) || "Stream failed");
      }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }
        buffer += decoder.decode(value, { stream: true });
        const chunks = buffer.split("\n\n");
        buffer = chunks.pop() ?? "";
        for (const chunk of chunks) {
          const event = parseSse(chunk);
          if (event?.event === "update") {
            const names = Object.keys(JSON.parse(event.data) as Record<string, unknown>);
            setLog((current) => [...current, `Agent: ${names.join(", ")}`]);
          }
          if (event?.event === "done") {
            const payload = JSON.parse(event.data) as {
              answer?: string;
              awaiting_human?: boolean;
            };
            if (payload.answer) {
              setLog((current) => [...current, `Support: ${payload.answer}`]);
            }
            if (payload.awaiting_human) {
              setLog((current) => [
                ...current,
                "A specialist has been assigned. You can keep this page open for updates.",
              ]);
            }
          }
          if (event?.event === "error") {
            setError(event.data);
          }
        }
      }
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm text-[var(--muted)]">Ticket {ticket.id.slice(0, 8)}</p>
          <h1 className="font-[family-name:var(--font-serif)] text-3xl">{ticket.subject}</h1>
        </div>
        <StatusBadge status={ticket.status} />
      </div>
      <section className="rounded-2xl border border-[var(--line)] bg-[var(--card)] p-5">
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-[var(--muted)]">
          Conversation
        </h2>
        <div className="grid gap-3 text-sm leading-6">
          <p className="whitespace-pre-wrap text-[var(--muted)]">{ticket.description}</p>
          {ticket.resolution ? (
            <p className="whitespace-pre-wrap rounded-xl bg-[#f6efe4] p-4">{ticket.resolution}</p>
          ) : null}
          {log.map((line, index) => (
            <p key={`${index}-${line.slice(0, 24)}`} className="whitespace-pre-wrap">
              {line}
            </p>
          ))}
        </div>
      </section>
      {ticket.status === "resolved" || ticket.status === "closed" ? null : (
        <form
          className="grid gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            if (message.trim()) {
              void run(message.trim());
            }
          }}
        >
          <textarea
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            rows={4}
            className="rounded-xl border border-[var(--line)] bg-white px-3 py-2"
            disabled={busy}
          />
          {error ? <p className="text-sm text-rose-700">{error}</p> : null}
          <button
            type="submit"
            disabled={busy || !message.trim()}
            className="justify-self-start rounded-full bg-[var(--accent)] px-5 py-2.5 text-sm font-medium text-[var(--accent-ink)] disabled:opacity-60"
          >
            {busy ? "Working…" : "Ask the assistant"}
          </button>
        </form>
      )}
    </div>
  );
}

function parseSse(chunk: string): { event: string; data: string } | null {
  let event = "message";
  const dataLines: string[] = [];
  for (const line of chunk.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
  }
  if (dataLines.length === 0) {
    return null;
  }
  return { event, data: dataLines.join("\n") };
}
