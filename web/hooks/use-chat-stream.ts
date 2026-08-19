"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type {
  ChatMessage,
  ChatStreamEvent,
  ResolutionResponse,
  TicketStatus,
} from "@/lib/api/types";

const liveCache = new Map<string, ChatMessage[]>();

function parseSse(chunk: string): { event: string; data: string } | null {
  let event = "message";
  const dataLines: string[] = [];
  for (const line of chunk.split("\n")) {
    const normalized = line.replace(/\r$/, "");
    if (normalized.startsWith("event:")) {
      event = normalized.slice(6).trim();
    } else if (normalized.startsWith("data:")) {
      dataLines.push(normalized.slice(5).trim());
    }
  }
  if (dataLines.length === 0) {
    return null;
  }
  return { event, data: dataLines.join("\n") };
}

function splitSseFrames(buffer: string): { frames: string[]; rest: string } {
  const normalized = buffer.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  const parts = normalized.split("\n\n");
  const rest = parts.pop() ?? "";
  return { frames: parts, rest };
}

function parseStreamEvent(rawEvent: string, rawData: string): ChatStreamEvent | null {
  let data: unknown;
  try {
    data = JSON.parse(rawData);
  } catch {
    return { event: "error", data: { error: rawData } };
  }
  if (rawEvent === "token") {
    const text = typeof data === "object" && data && "text" in data ? String(data.text ?? "") : "";
    return { event: "token", data: { text } };
  }
  if (rawEvent === "message" && isChatMessage(data)) {
    return { event: "message", data };
  }
  if (rawEvent === "done") {
    return { event: "done", data: data as ResolutionResponse };
  }
  if (rawEvent === "error") {
    const error =
      typeof data === "object" && data && "error" in data
        ? String((data as { error: unknown }).error)
        : rawData;
    return { event: "error", data: { error } };
  }
  if (rawEvent === "ticket_status") {
    const payload = data as { status?: string; assigned_agent?: string | null };
    if (typeof payload.status !== "string") {
      return null;
    }
    return {
      event: "ticket_status",
      data: {
        status: payload.status as TicketStatus,
        assigned_agent: payload.assigned_agent ?? null,
      },
    };
  }
  if (rawEvent === "status" || rawEvent === "tool" || rawEvent === "heartbeat") {
    return { event: rawEvent, data } as ChatStreamEvent;
  }
  if (isChatMessage(data)) {
    return { event: "message", data };
  }
  return null;
}

function isChatMessage(value: unknown): value is ChatMessage {
  if (!value || typeof value !== "object") {
    return false;
  }
  const item = value as Record<string, unknown>;
  return (
    typeof item.id === "string" &&
    item.id.length > 0 &&
    typeof item.role === "string" &&
    typeof item.content === "string" &&
    item.content.length > 0
  );
}

function fingerprint(message: ChatMessage): string {
  const family =
    message.role === "assistant" || message.role === "human_agent" ? "agent" : message.role;
  return `${family}:${message.content}`;
}

function mergePreferLive(live: ChatMessage[], incoming: ChatMessage[]): ChatMessage[] {
  const ids = new Set(live.map((item) => item.id));
  const prints = new Set(live.map(fingerprint));
  const extras = incoming.filter(
    (item) => !ids.has(item.id) && !prints.has(fingerprint(item)) && !item.id.startsWith("local-"),
  );
  return extras.length ? [...live, ...extras] : live;
}

function readCache(ticketId: string | null, initial: ChatMessage[]): ChatMessage[] {
  if (!ticketId) {
    return initial;
  }
  const cached = liveCache.get(ticketId);
  if (!cached || cached.length === 0) {
    return initial;
  }
  return mergePreferLive(cached, initial);
}

function emitSseFrames(frames: string[], onEvent: (event: ChatStreamEvent) => void): void {
  for (const frame of frames) {
    const parsed = parseSse(frame);
    if (!parsed) {
      continue;
    }
    const event = parseStreamEvent(parsed.event, parsed.data);
    if (event) {
      onEvent(event);
    }
  }
}

async function readSseStream(
  response: Response,
  onEvent: (event: ChatStreamEvent) => void,
): Promise<void> {
  if (!response.body) {
    throw new Error("Stream failed");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      buffer += decoder.decode();
      const leftover = buffer.replace(/\r\n/g, "\n").replace(/\r/g, "\n").trim();
      if (leftover) {
        emitSseFrames(leftover.split("\n\n"), onEvent);
      }
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const { frames, rest } = splitSseFrames(buffer);
    buffer = rest;
    emitSseFrames(frames, onEvent);
  }
}

function assistantFromDone(data: ResolutionResponse, fallback: string): ChatMessage | null {
  const content = data.answer || fallback;
  if (!content) {
    return null;
  }
  return {
    id: data.run_id || `done-${data.ticket_id}-${content.slice(0, 24)}`,
    ticket_id: String(data.ticket_id),
    role: "assistant",
    content,
    agent_run_id: data.run_id,
    created_at: new Date().toISOString(),
  };
}

export function useChatStream(
  ticketId: string | null,
  initial: ChatMessage[],
  initialStatus: TicketStatus = "open",
) {
  const [messages, setMessages] = useState<ChatMessage[]>(() => readCache(ticketId, initial));
  const [activeId, setActiveId] = useState(ticketId);
  const [status, setStatus] = useState<TicketStatus>(initialStatus);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const draftRef = useRef("");
  const sendingRef = useRef(false);

  if (ticketId !== activeId) {
    setActiveId(ticketId);
    setMessages(readCache(ticketId, initial));
    setStatus(initialStatus);
    setDraft("");
    draftRef.current = "";
  }

  const upsert = useCallback(
    (message: ChatMessage) => {
      if (!isChatMessage(message)) {
        return;
      }
      setMessages((current) => {
        const withoutLocal = current.filter(
          (item) =>
            !(
              item.id.startsWith("local-") &&
              item.role === message.role &&
              item.content === message.content
            ),
        );
        if (withoutLocal.some((item) => item.id === message.id)) {
          if (ticketId) {
            liveCache.set(ticketId, withoutLocal);
          }
          return withoutLocal;
        }
        if (withoutLocal.some((item) => fingerprint(item) === fingerprint(message))) {
          if (ticketId) {
            liveCache.set(ticketId, withoutLocal);
          }
          return withoutLocal;
        }
        const next = [...withoutLocal, message];
        if (ticketId) {
          liveCache.set(ticketId, next);
        }
        return next;
      });
    },
    [ticketId],
  );

  useEffect(() => {
    if (!ticketId) {
      return;
    }
    const source = new EventSource(`/api/support/tickets/${ticketId}/events`);
    const apply = (name: string) => (event: MessageEvent<string>) => {
      if (sendingRef.current) {
        return;
      }
      const parsed = parseStreamEvent(name, event.data);
      if (parsed?.event === "message") {
        upsert(parsed.data);
      }
      if (parsed?.event === "done") {
        const assistant = assistantFromDone(parsed.data, "");
        if (assistant) {
          upsert(assistant);
        }
      }
    };
    source.addEventListener("message", apply("message"));
    source.addEventListener("done", apply("done"));
    source.addEventListener("ticket_status", (event: MessageEvent<string>) => {
      const parsed = parseStreamEvent("ticket_status", event.data);
      if (parsed?.event === "ticket_status") {
        setStatus(parsed.data.status);
      }
    });
    return () => {
      source.close();
    };
  }, [ticketId, upsert]);

  const send = useCallback(
    async (content: string, id = ticketId, role: "customer" | "human_agent" = "customer") => {
      if (!id) {
        throw new Error("Missing ticket");
      }
      setBusy(true);
      setError(null);
      setDraft("");
      draftRef.current = "";
      sendingRef.current = true;
      let committedAssistant = false;
      const optimistic: ChatMessage = {
        id: `local-${Date.now()}`,
        ticket_id: id,
        role,
        content,
        agent_run_id: null,
        created_at: new Date().toISOString(),
      };
      upsert(optimistic);
      try {
        const response = await fetch(`/api/support/tickets/${id}/messages`, {
          method: "POST",
          headers: {
            Accept: "text/event-stream",
            "Content-Type": "application/json",
          },
          cache: "no-store",
          body: JSON.stringify({ content, role }),
        });
        if (!response.ok) {
          throw new Error((await response.text()) || "Send failed");
        }
        await readSseStream(response, (event) => {
          if (event.event === "token" && event.data.text) {
            setDraft((current) => {
              const next = current + event.data.text;
              draftRef.current = next;
              return next;
            });
          }
          if (event.event === "message") {
            upsert(event.data);
            if (event.data.role === "assistant") {
              committedAssistant = true;
              draftRef.current = "";
              setDraft("");
            }
          }
          if (event.event === "done") {
            if (role !== "human_agent") {
              const assistant = assistantFromDone(event.data, draftRef.current);
              if (assistant) {
                upsert(assistant);
              }
            }
            committedAssistant = true;
            draftRef.current = "";
            setDraft("");
          }
          if (event.event === "ticket_status") {
            setStatus(event.data.status);
          }
          if (event.event === "error") {
            setError(event.data.error);
          }
        });
        if (!committedAssistant && draftRef.current) {
          upsert({
            id: `draft-${id}-${Date.now()}`,
            ticket_id: id,
            role: "assistant",
            content: draftRef.current,
            agent_run_id: null,
            created_at: new Date().toISOString(),
          });
          draftRef.current = "";
          setDraft("");
        }
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Send failed");
      } finally {
        sendingRef.current = false;
        setBusy(false);
      }
    },
    [ticketId, upsert],
  );

  return { messages, draft, busy, error, status, setStatus, send, setError };
}
