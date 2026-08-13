import type {
  AgentEventListResponse,
  AgentRunListResponse,
  AnalyticsOverviewResponse,
  AnalyticsToolsResponse,
  CreateTicketRequest,
  ResolutionResponse,
  TicketListResponse,
  TicketResponse,
} from "@/lib/api/types";

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
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "X-API-Key": API_KEY,
      "Content-Type": "application/json",
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

export function createTicket(body: CreateTicketRequest): Promise<TicketResponse> {
  return apiFetch<TicketResponse>("/tickets", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getTicket(ticketId: string): Promise<TicketResponse> {
  return apiFetch<TicketResponse>(`/tickets/${ticketId}`);
}

export function listTickets(params: URLSearchParams): Promise<TicketListResponse> {
  const query = params.toString();
  return apiFetch<TicketListResponse>(`/tickets${query ? `?${query}` : ""}`);
}

export function listEscalations(limit = 50): Promise<TicketListResponse> {
  return apiFetch<TicketListResponse>(`/escalations?limit=${limit}`);
}

export function resolveTicket(
  ticketId: string,
  content: string,
): Promise<ResolutionResponse> {
  return apiFetch<ResolutionResponse>(`/tickets/${ticketId}/resolve`, {
    method: "POST",
    body: JSON.stringify({
      messages: [{ role: "user", content }],
    }),
  });
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
