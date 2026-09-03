# Runtime invariants — ORM async + live chat

These are **project-wide** paths. If the task is to change portal/SSE/chat code, invoke **realtime-chat** after reading this file. Do not re-discover these bugs from scratch.

## 1. AsyncSession: never lazy-load relationships

**Symptom (portal home, "Como podemos ajudar hoje?"):**

```json
{"detail":"Internal server error","error":"greenlet_spawn has not been called; can't call await_only() here. Was IO attempted in an unexpected place?"}
```

SQLAlchemy docs: https://sqlalche.me/e/20/xd2s (`MissingGreenlet`).

**Cause:** `ticket_to_response()` / `ticket_to_summary()` read `ticket.customer` and `ticket.resolution`. After `session.add` + `flush`, those relationships are not loaded. Accessing them under `AsyncSession` does sync IO and raises.

**Where it broke:** `POST /portal/conversations` in `app/api/routes/portal.py` returned `ticket_to_response(ticket)` on a freshly flushed row.

**Required pattern** (same as `close_ticket` / `confirm_resolution` / `assign_agent`):

```python
session.add(ticket)
await session.flush()
loaded = await ticket_service.get_ticket_or_404(session, ticket.id)
return ticket_service.ticket_to_response(loaded)
```

`get_ticket_or_404` already uses `selectinload(Ticket.customer)` and `selectinload(Ticket.resolution)`.

**Also valid:** build the DTO with scalars already in memory (`customer.email`, `customer.name`) and **do not** touch `ticket.customer` — see `POST /tickets` in `app/api/routes/tickets.py`.

**Do not:** `await session.refresh(ticket)` of timestamps only, then call `ticket_to_response(ticket)`. Refresh of `created_at` does not load relationships.

**Do not:** access `ticket.customer` or `ticket.resolution` after `flush` without `selectinload` or a reload.

Any new endpoint that returns `TicketResponse` after insert/update must reload with relationships or map fields without lazy IO.

---

## 2. Live chat: assistant reply must stay on screen without a browser refresh

Two stacked failures produced: "I send a message, the answer flashes then vanishes; F5 shows it."

The graph **does persist** `ticket_messages`. The bug is transport + React state, not the LLM.

### 2a. POST SSE parser (`web/hooks/use-chat-stream.ts`)

`sse-starlette` emits `\r\n\r\n` between events. Splitting only on `"\n\n"` never frames events. The last event (`message` / `done`) often sits in the leftover buffer; if you `break` on stream end without flushing, the UI never commits the assistant turn.

**Required:**

- Normalize `\r\n` → `\n` before splitting frames
- On `reader.read()` `done`, flush leftover buffer
- Treat `done.answer` as the assistant bubble (fallback if the `message` event is missed)
- Keep a draft until it is committed into `messages`

### 2b. Do not reset live messages from stale RSC props

`/tickets/[id]` is a Server Component. After POST completes, Next.js may re-render the page with the **first-load** `initialMessages` (client router cache), which does not include the new assistant row.

**Wrong:** `useEffect(() => setMessages(initial), [ticketId])` or `[initial]` — remount/re-render wipes the live transcript ~1s after it appears.

**Required** (`web/hooks/use-chat-stream.ts`):

- Module-level cache keyed by `ticketId` so remount restores live messages
- Merge server `initial` **additively**; never replace a longer live list with a shorter stale snapshot
- Deduplicate by message `id` **in current state**, not a `seen` set that outlives a reset (that combination drops the bubble)

### 2c. Redis fan-out must not kill the EventSource

**Symptom:** Next.js logs `GET /api/support/tickets/{id}/events 200 in ~15.1s` on a loop (heartbeat interval). The SSE connection closes every idle period; the console/portal miss live turns.

**Cause:** `asyncio.wait_for(pubsub.listen().__anext__(), timeout=heartbeat)` **cancels** the listen iterator. The next `__anext__` raises `StopAsyncIteration` and the generator ends.

**Required** (`app/services/chat_bus.py` `subscribe_ticket_events`):

```python
message = await pubsub.get_message(
    ignore_subscribe_messages=True,
    timeout=idle_timeout,
)
if message is None:
    yield heartbeat
    continue
```

Do **not** wrap `pubsub.listen()` in `asyncio.wait_for`.

Python chat changes need an API **process restart** if you started the server with `uv run python scripts/run_api.py` (no reload). Next.js HMR is not enough.

### 2d. Do not duplicate the assistant bubble (tokens + leftover draft)

**Symptom:** The same Portuguese reply appears twice, or the second bubble is the text glued to itself with no newline (`resposta` + `resposta`).

**Cause (stacked):**

1. LangGraph `stream_mode="messages"` emits incremental `AIMessageChunk` tokens **and** the complete `AIMessage` the worker returns in `{"messages": [...]}`. `_token_text` that accepts any string content concatenates tokens + full message.
2. After `done`, `setDraft("")` does not clear `draftRef` until the next render. A leftover-draft upsert then commits the concatenated string as a second bubble (`draft-${id}-…`) with a different fingerprint.
3. POST SSE already delivers `message` / `done`; the same events also arrive on `GET /events` (Redis). Applying both while the POST is in flight doubles the turn.

**Required:**

- `_token_text` in `app/services/chat_service.py`: only types whose name ends with `Chunk` (skip complete `AIMessage` and tool-call chunks).
- On `done` or assistant `message`: clear `draftRef` immediately; do **not** upsert leftover draft if that turn already committed.
- While POST `/messages` is in flight, ignore EventSource `message` / `done` (`sendingRef`).
- Fingerprint `assistant` and `human_agent` as the same family (`agent:${content}`) so identical staff text is one bubble.

`done.answer` remains the fallback when the `message` event is missed — that is still required by 2a. It must not create a **second** bubble when the content is already on screen.

### 2e. Human console reply must persist once

**Symptom:** The specialist's message (e.g. "Olá Ana, … reembolso …") appears twice in the portal and console.

**Cause:** `stream_human_turn` already `append_message(..., HUMAN_AGENT)`. Then either:

- no graph interrupt → `done` with `answer: content`, and the hook turns `done.answer` into an `assistant` bubble; or
- interrupt resume → `persist_graph_result` always appends `ASSISTANT` with the same text, then `_publish_assistant_and_done` fans it out.

Fingerprint by `role:content` does **not** collapse `human_agent` vs `assistant`.

**Required:**

- `should_persist_assistant_message` in `app/services/ticket_service.py`: skip the assistant row when the last message is already `human_agent` or `assistant` with the same stripped text.
- Non-interrupted human turn: persist + publish `message` only; `done.answer` must be empty (transport spec).
- Hook: do not map `done` → assistant bubble when the send role is `human_agent`. Still upsert EventSource `message` for the other party.

---

## 3. Escalation reason is internal, never customer-facing

**Symptom:** The bubble contains the agent reply, then `Escalation reason:` plus the same reply again.

**Cause:** `run_escalation_agent` did `draft_answer + "\n\nEscalation reason: " + reason` while `escalation_node` passed `reason=draft_answer`. Interrupt persist used that string as the chat row **before** `output_guardrails`.

**Required:**

- `draft_answer` = customer-facing text only (worker reply or `CUSTOMER_ESCALATION_MESSAGE`).
- `reason` / `escalation_reason` stay on the interrupt payload for the console, not in `ticket_messages`.
- `sanitize_customer_answer` in `app/security/guardrails.py` (called from `validate_output` and `persist_graph_result`) strips `Escalation reason:` blocks and collapses an identical reply pasted 2–4 times.
- Persist never falls back to interrupt `reason` as the customer answer.
- `run_escalation_agent` / `customer_escalation_reply` always include an explicit specialist-handoff sentence in `draft_answer`.

---

## 4. Human takeover silences the AI

**Symptom:** A console agent clicks "Assumir conversa". The customer replies. The LangGraph worker answers anyway and talks over the human.

**Cause:** `POST /tickets/{id}/messages` with `role=customer` always called `stream_customer_turn` → `stream_graph_events`, ignoring `tickets.assigned_agent`.

**Required:** `customer_turn_runs_graph` in `app/services/chat_service.py`. When `assigned_agent` is set, persist the customer row, publish `message` + `done` with an empty `answer`, and **do not** invoke the graph. Human replies still use `stream_human_turn` (resume interrupt if present).

---

## 5. Paths (do not invent new ones)

| Concern | Path |
|---------|------|
| Portal create conversation | `app/api/routes/portal.py` → `POST /portal/conversations` |
| Ticket DTO + reload | `app/services/ticket_service.py` → `get_ticket_or_404`, `ticket_to_response` |
| POST stream + persist | `app/services/chat_service.py` → `stream_customer_turn`, `stream_human_turn`, `_token_text`, `customer_turn_runs_graph` |
| Skip duplicate assistant row | `app/services/ticket_service.py` → `should_persist_assistant_message` |
| Customer-facing sanitizer | `app/security/guardrails.py` → `sanitize_customer_answer` |
| Escalation payload | `app/agents/escalation.py`, `app/graph/nodes.py` `escalation_node` |
| Redis pub/sub | `app/services/chat_bus.py` |
| SSE routes | `app/api/routes/tickets.py` → `POST /{id}/messages`, `GET /{id}/events` |
| BFF stream proxy | `web/app/api/support/[...path]/route.ts` |
| Chat hook | `web/hooks/use-chat-stream.ts` |
| Home composer | `web/components/portal/chat-window.tsx` (`NewConversation`) |

Transport remains **SSE + Redis**. Do not add WebSockets.

For identity-first prompts, portal cookies, and console inbox, continue in **realtime-chat**.
