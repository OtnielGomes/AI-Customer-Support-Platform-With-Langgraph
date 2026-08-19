import type {
  AgentEventListResponse,
  AgentRunListResponse,
  AnalyticsOverviewResponse,
  AnalyticsToolsResponse,
  ChatMessageListResponse,
  PortalMe,
  ResolutionResponse,
  TicketListResponse,
  TicketResponse,
} from "@/lib/api/types";
import { getPortalEmail } from "@/lib/auth";

const API_URL = process.env.SUPPORT_API_URL ?? "http://localhost:8000";
const API_KEY = process.env.SUPPORT_API_KEY ?? "";

function apiError(status: number, body: string): Error {
  try {
    const parsed = JSON.parse(body) as { detail?: unknown };
    if (typeof parsed.detail === "string") {
      return new Error(parsed.detail);
    }
  } catch {
    /* use raw body */
  }
  return new Error(body || `Request failed (${status})`);
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const email = await getPortalEmail();
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "X-API-Key": API_KEY,
      "Content-Type": "application/json",
      ...(email ? { "X-Customer-Email": email } : {}),
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!response.ok) {
    throw apiError(response.status, await response.text());
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function getPortalMe(): Promise<PortalMe> {
  return apiFetch<PortalMe>("/portal/me");
}

export function validatePortalSession(email: string): Promise<PortalMe> {
  return apiFetch<PortalMe>("/portal/session", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export function createConversation(orderId?: string | null): Promise<TicketResponse> {
  return apiFetch<TicketResponse>("/portal/conversations", {
    method: "POST",
    body: JSON.stringify({ order_id: orderId || null }),
  });
}

export function listTicketMessages(ticketId: string): Promise<ChatMessageListResponse> {
  return apiFetch<ChatMessageListResponse>(`/tickets/${ticketId}/messages`);
}

export function takeoverTicket(ticketId: string, agent = "console"): Promise<TicketResponse> {
  return apiFetch<TicketResponse>(`/tickets/${ticketId}/takeover`, {
    method: "POST",
    body: JSON.stringify({ agent }),
  });
}

export function getTicket(ticketId: string): Promise<TicketResponse> {
  return apiFetch<TicketResponse>(`/tickets/${ticketId}`);
}

export function listTickets(params: URLSearchParams): Promise<TicketListResponse> {
  const query = params.toString();
  return apiFetch<TicketListResponse>(`/tickets${query ? `?${query}` : ""}`);
}

export function replyToEscalation(
  ticketId: string,
  answer: string,
  agent = "console",
): Promise<ResolutionResponse> {
  return apiFetch<ResolutionResponse>(`/tickets/${ticketId}/escalation/reply`, {
    method: "POST",
    body: JSON.stringify({ answer, agent }),
  });
}

export function closeTicket(ticketId: string, reason?: string): Promise<TicketResponse> {
  return apiFetch<TicketResponse>(`/tickets/${ticketId}/close`, {
    method: "POST",
    body: JSON.stringify({ reason: reason || null }),
  });
}

export function confirmTicket(ticketId: string): Promise<TicketResponse> {
  return apiFetch<TicketResponse>(`/tickets/${ticketId}/confirm`, {
    method: "POST",
    body: "{}",
  });
}

export function listRuns(ticketId: string): Promise<AgentRunListResponse> {
  return apiFetch<AgentRunListResponse>(`/tickets/${ticketId}/runs`);
}

export function listRunEvents(runId: string): Promise<AgentEventListResponse> {
  return apiFetch<AgentEventListResponse>(`/runs/${runId}/events`);
}

export function getAnalyticsOverview(): Promise<AnalyticsOverviewResponse> {
  return apiFetch<AnalyticsOverviewResponse>("/analytics/overview");
}

export function getToolAnalytics(): Promise<AnalyticsToolsResponse> {
  return apiFetch<AnalyticsToolsResponse>("/analytics/tools");
}
