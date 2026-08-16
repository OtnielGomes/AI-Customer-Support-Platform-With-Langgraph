"use client";

import { useState, useTransition } from "react";

import type { TicketResponse, TicketStatus } from "@/lib/api/types";
import { StatusBadge } from "@/components/status-badge";

interface TicketChatProps {
  ticket: TicketResponse;
}

export function TicketChat({ ticket }: TicketChatProps) {
  const [status, setStatus] = useState<TicketStatus>(ticket.status);
  const [resolution, setResolution] = useState(ticket.resolution);
  const [message, setMessage] = useState(ticket.resolution ? "" : ticket.description);
  const [log, setLog] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [askIfResolved, setAskIfResolved] = useState(
    Boolean(ticket.resolution) && ticket.status !== "closed",
  );
  const [finished, setFinished] = useState(ticket.status === "closed");
  const [busy, startTransition] = useTransition();

  const conversationClosed = status === "closed" || finished;

  function run(content: string) {
    startTransition(async () => {
      setError(null);
      setAskIfResolved(false);
      setFinished(false);
      setLog((current) => [...current, `You: ${content}`]);
      setMessage("");
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
        let awaitingHuman = false;
        let answer = "";
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
                answer = payload.answer;
                setResolution(payload.answer);
                setLog((current) => [...current, `Support: ${payload.answer}`]);
              }
              awaitingHuman = Boolean(payload.awaiting_human);
              if (payload.awaiting_human) {
                setStatus("escalated");
                setLog((current) => [
                  ...current,
                  "A specialist has been assigned. You can keep this page open for updates.",
                ]);
              } else {
                setStatus("in_progress");
              }
            }
            if (event?.event === "error") {
              setError(event.data);
            }
          }
        }
        if (answer && !awaitingHuman) {
          setAskIfResolved(true);
        }
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Request failed");
      }
    });
  }

  function confirmResolved() {
    startTransition(async () => {
      setError(null);
      try {
        const response = await fetch(`/api/support/tickets/${ticket.id}/confirm`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: "{}",
        });
        if (!response.ok) {
          throw new Error((await response.text()) || "Could not confirm resolution");
        }
        setStatus("resolved");
        setAskIfResolved(false);
        setFinished(true);
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Could not confirm resolution");
      }
    });
  }

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm text-[var(--muted)]">Ticket {ticket.id.slice(0, 8)}</p>
          <h1 className="font-[family-name:var(--font-serif)] text-3xl">{ticket.subject}</h1>
        </div>
        <StatusBadge status={status} />
      </div>
      <section className="rounded-2xl border border-[var(--line)] bg-[var(--card)] p-5">
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-[var(--muted)]">
          Conversation
        </h2>
        <div className="grid gap-3 text-sm leading-6">
          <p className="whitespace-pre-wrap text-[var(--muted)]">{ticket.description}</p>
          {resolution && log.length === 0 ? (
            <p className="whitespace-pre-wrap rounded-xl bg-[#f6efe4] p-4">{resolution}</p>
          ) : null}
          {log.map((line, index) => (
            <p key={`${index}-${line.slice(0, 24)}`} className="whitespace-pre-wrap">
              {line}
            </p>
          ))}
        </div>
      </section>
      {askIfResolved && !conversationClosed ? (
        <section className="rounded-2xl border border-[var(--line)] bg-[var(--card)] p-5">
          <p className="text-sm font-medium">Did this resolve your issue?</p>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Confirm if the answer helped, or send another message if you still need support.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={busy}
              onClick={confirmResolved}
              className="rounded-full bg-[var(--accent)] px-5 py-2.5 text-sm font-medium text-[var(--accent-ink)] disabled:opacity-60"
            >
              Yes, it&apos;s resolved
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => setAskIfResolved(false)}
              className="rounded-full border border-[var(--line)] px-5 py-2.5 text-sm disabled:opacity-60"
            >
              No, I still need help
            </button>
          </div>
        </section>
      ) : null}
      {conversationClosed ? (
        <p className="text-sm text-[var(--muted)]">
          This ticket is {status}. Open a new ticket if you need more help.
        </p>
      ) : (
        <form
          className="grid gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            if (message.trim()) {
              run(message.trim());
            }
          }}
        >
          <textarea
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            rows={4}
            placeholder="Add more details or ask a follow-up question…"
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
