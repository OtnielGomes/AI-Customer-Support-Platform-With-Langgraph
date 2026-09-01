/**
 * Hand-written DTOs aligned with `app/api/schemas.py`.
 * Regenerate a full OpenAPI dump with `npm run generate:types` when the API is running.
 */
export type TicketStatus =
  | "open"
  | "in_progress"
  | "resolved"
  | "escalated"
  | "closed";

export type TicketIntent = "billing" | "logistics" | "account" | "unknown";

export type AgentRunStatus =
  | "running"
  | "completed"
  | "awaiting_human"
  | "failed";

export type AgentEventType =
  | "node"
  | "tool"
  | "llm"
  | "retrieval"
  | "guardrail";

export type ChatMessageRole = "customer" | "assistant" | "human_agent" | "system";

export interface TicketSummary {
  id: string;
  customer_id: string;
  customer_email: string | null;
  customer_name: string | null;
  subject: string;
  status: TicketStatus;
  intent: TicketIntent | null;
  escalated: boolean;
  escalated_at: string | null;
  last_message_at: string | null;
  assigned_agent: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface TicketListResponse {
  items: TicketSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface TicketResponse {
  id: string;
  customer_id: string;
  customer_email: string | null;
  customer_name: string | null;
  subject: string;
  description: string;
  status: TicketStatus;
  intent: TicketIntent | null;
  escalated_at: string | null;
  resolution: string | null;
  escalated: boolean;
  order_id: string | null;
  order: OrderSummary | null;
  last_message_at: string | null;
  assigned_agent: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface OrderItemSummary {
  product_name: string;
  quantity: number;
  line_total: string;
}

export interface OrderSummary {
  id: string;
  public_id: string;
  display_number: string;
  status: string;
  status_label: string;
  payment_status: string;
  payment_status_label: string;
  paid_payment_count: number;
  total_amount: string;
  currency: string;
  created_at: string | null;
  estimated_delivery: string | null;
  actual_delivery: string | null;
  items: OrderItemSummary[];
}

export interface ChatMessage {
  id: string;
  ticket_id: string;
  role: ChatMessageRole;
  content: string;
  agent_run_id: string | null;
  created_at: string | null;
}

export interface ChatMessageListResponse {
  items: ChatMessage[];
}

export interface TicketStatusEvent {
  status: TicketStatus;
  assigned_agent: string | null;
}

export type ChatStreamEvent =
  | { event: "token"; data: { text: string } }
  | { event: "message"; data: ChatMessage }
  | { event: "status"; data: { nodes?: string[] } }
  | { event: "ticket_status"; data: TicketStatusEvent }
  | { event: "tool"; data: { name: string; status: string } }
  | { event: "done"; data: ResolutionResponse }
  | { event: "error"; data: { error: string } }
  | { event: "heartbeat"; data: { ts: string } };

export interface PortalMe {
  id: string;
  public_id: string;
  email: string;
  name: string;
  customer_tier: string;
  account_status: string;
  orders: OrderSummary[];
  conversations: TicketSummary[];
}

export interface ResolutionResponse {
  ticket_id: string;
  answer: string;
  intent: string | null;
  confidence: number | null;
  escalated: boolean;
  awaiting_human: boolean;
  run_id: string | null;
  tool_results: Record<string, unknown>[];
  retrieved_context: Record<string, unknown>[];
  interrupt_payload: Record<string, unknown> | null;
}

export interface AgentRunResponse {
  id: string;
  ticket_id: string;
  thread_id: string;
  status: AgentRunStatus;
  intent: string | null;
  confidence: number | null;
  escalated: boolean;
  total_latency_ms: number | null;
  error: string | null;
  created_at: string;
}

export interface AgentRunListResponse {
  items: AgentRunResponse[];
}

export interface AgentEventResponse {
  id: string;
  run_id: string;
  sequence: number;
  event_type: AgentEventType;
  name: string;
  input: Record<string, unknown> | null;
  output: Record<string, unknown> | null;
  latency_ms: number | null;
  error: string | null;
  created_at: string;
}

export interface AgentEventListResponse {
  items: AgentEventResponse[];
}

export interface VolumePoint {
  date: string;
  count: number;
}

export interface AnalyticsOverviewResponse {
  total_tickets: number;
  by_status: Record<string, number>;
  by_intent: Record<string, number>;
  escalation_rate: number;
  avg_confidence: number | null;
  avg_resolution_ms: number | null;
  volume_by_day: VolumePoint[];
}

export interface ToolAnalyticsItem {
  name: string;
  calls: number;
  errors: number;
  error_rate: number;
  avg_latency_ms: number | null;
  p95_latency_ms: number | null;
}

export interface AnalyticsToolsResponse {
  items: ToolAnalyticsItem[];
}

export interface CreateTicketRequest {
  customer_email: string;
  customer_name: string;
  subject: string;
  description: string;
}
