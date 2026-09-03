# Chat transport (SSE + Redis)

Do not introduce WebSockets. The Next.js BFF already streams HTTP bodies with `duplex: "half"`.

## Channels

Redis pub/sub channel: `ticket:{ticket_id}:events`.

Publisher: `app/services/chat_bus.py` (`publish_ticket_event`).
Subscriber: `GET /tickets/{id}/events` and the POST SSE generator (so the writer also sees fan-out from the other party).

Heartbeat every `CHAT_STREAM_HEARTBEAT_SECONDS` (default 15). Event name: `heartbeat`. Payload: `{"ts": "<iso>"}`.

## Write path — `POST /tickets/{id}/messages`

Request JSON:

```json
{
  "content": "Meu pedido atrasou",
  "role": "customer",
  "order_id": null
}
```

`role` is `customer` on the portal and `human_agent` on the console. Persist first, then:

1. If `role=human_agent` and graph snapshot has an interrupt → `Command(resume={"answer", "agent"})`.
2. If `role=human_agent` and no interrupt → persist + publish `message` only (no graph).
3. If `role=customer` and `assigned_agent` is set → persist + publish `message` only (no graph). The human owns the thread.
4. If `role=customer` and no assignee → run graph with `stream_mode=["updates", "messages"]`.

SSE events from this POST (and mirrored on the bus):

| event | data | when |
|-------|------|------|
| `message` | `{id, role, content, created_at}` | persisted user or human message |
| `status` | `{status, node?}` | graph node started (`updates`) |
| `tool` | `{name, status}` | tool call seen |
| `token` | `{text}` | LLM token from `messages` stream |
| `done` | `ResolutionResponse` JSON | graph finished; assistant message persisted |
| `error` | `{error}` | failure |
| `heartbeat` | `{ts}` | keep-alive |

LangGraph: read **langgraph-docs** before changing `stream_mode`. `messages` mode yields `(token, metadata)` tuples; filter to incremental **`AIMessageChunk`** from the worker LLM. Skip complete node-returned `AIMessage`s and tool JSON — treating those as `token`s concatenates the reply onto itself.

Human `done`: when there is **no** interrupt, do not put the human text in `done.answer` (empty string). The `message` event is the chat row. After HITL resume, `persist_graph_result` must not insert a second `assistant` row with the same body (`should_persist_assistant_message`).

## Read path — `GET /tickets/{id}/events`

Passive EventSource. Auth: API key + optional `X-Customer-Email` (ownership). Console uses API key only.

On connect, do **not** replay history (client loads `GET /tickets/{id}/messages`). Stream only new bus events + heartbeats.

Heartbeat implementation (`app/services/chat_bus.py` `subscribe_ticket_events`): use `pubsub.get_message(ignore_subscribe_messages=True, timeout=idle_timeout)` and yield `heartbeat` when the result is `None`. **Do not** wrap `pubsub.listen()` in `asyncio.wait_for` — cancelling `__anext__` kills the iterator, the SSE generator ends, and Next.js logs `GET /events 200 in ~15s` on a reconnect loop.

Python API via `scripts/run_api.py` has no reload; restart it after chat_bus changes.

## Deprecated

`POST /tickets/{id}/stream` with `ResolveRequest.messages` remains as an alias that maps the last human content onto `/messages`. Do not use it from new UI.

## BFF

`web/app/api/support/[...path]/route.ts` must:

- Inject `X-API-Key`
- Inject `X-Customer-Email` from the signed `portal_session` cookie when present
- Copy upstream `content-type`
- Set `cache-control: no-cache` and `X-Accel-Buffering: no` on SSE responses
