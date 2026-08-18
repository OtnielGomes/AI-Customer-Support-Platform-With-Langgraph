"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ChatComposer } from "@/components/portal/chat-composer";
import { ChatTranscript } from "@/components/portal/chat-bubble";
import { TypingIndicator } from "@/components/portal/typing-indicator";
import { StatusBadge } from "@/components/status-badge";
import { useChatStream } from "@/hooks/use-chat-stream";
import type { ChatMessage, TicketResponse } from "@/lib/api/types";

export function ChatWindow({
  ticket,
  initialMessages,
  variant = "portal",
}: {
  ticket: TicketResponse;
  initialMessages: ChatMessage[];
  variant?: "portal" | "console";
}) {
  const { messages, draft, busy, error, send } = useChatStream(ticket.id, initialMessages);

  useEffect(() => {
    const key = `pending-chat:${ticket.id}`;
    const pending = sessionStorage.getItem(key);
    if (!pending) {
      return;
    }
    sessionStorage.removeItem(key);
    void send(pending);
  }, [ticket.id, send]);
  const live = [...messages];
  if (draft) {
    live.push({
      id: "draft",
      ticket_id: ticket.id,
      role: "assistant",
      content: draft,
      agent_run_id: null,
      created_at: null,
    });
  }

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm text-[var(--muted)]">Conversa {ticket.id.slice(0, 8)}</p>
          <h1 className="font-[family-name:var(--font-serif)] text-2xl">{ticket.subject}</h1>
        </div>
        <StatusBadge status={ticket.status} />
      </div>
      <section
        className={`max-h-[60vh] overflow-y-auto rounded-2xl border p-5 ${
          variant === "console" ? "border-white/10" : "border-[var(--line)] bg-[var(--card)]"
        }`}
      >
        <ChatTranscript messages={live} />
        <TypingIndicator visible={busy && !draft} />
      </section>
      {error ? <p className="text-sm text-rose-700">{error}</p> : null}
      {ticket.status === "closed" ? (
        <p className="text-sm text-[var(--muted)]">Esta conversa foi encerrada.</p>
      ) : (
        <ChatComposer
          disabled={busy}
          placeholder="Escreva sua mensagem…"
          onSend={(content) => {
            void send(content, ticket.id, variant === "console" ? "human_agent" : "customer");
          }}
        />
      )}
    </div>
  );
}

export function NewConversation({ orderId }: { orderId?: string | null }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  return (
    <div className="grid gap-2">
      <ChatComposer
        disabled={busy}
        placeholder="Como podemos ajudar hoje?"
        onSend={async (content) => {
          setBusy(true);
          setError(null);
          try {
            const created = await fetch("/api/support/portal/conversations", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ order_id: orderId || null }),
            });
            if (!created.ok) {
              throw new Error((await created.text()) || "Não foi possível abrir a conversa");
            }
            const ticket = (await created.json()) as { id: string };
            sessionStorage.setItem(`pending-chat:${ticket.id}`, content);
            router.push(`/tickets/${ticket.id}`);
          } catch (caught) {
            setError(caught instanceof Error ? caught.message : "Falha ao enviar");
            setBusy(false);
          }
        }}
      />
      {error ? <p className="text-sm text-rose-700">{error}</p> : null}
    </div>
  );
}
