# Troubleshooting — Local Development

## Windows + uv (hardlink error 396)

**Symptom:** `os error 396` or *cloud operation incompatible with hardlinks* during `uv sync`.

**Cause:** Project, `.venv`, or uv cache on OneDrive / cloud-synced folders.

**Fix:**

```powershell
$env:UV_LINK_MODE = "copy"
$env:UV_CACHE_DIR = "C:\uv-cache"
uv sync --link-mode=copy
```

`scripts/bootstrap.ps1` sets these automatically. Prefer cloning to `C:\dev\...` outside OneDrive when possible.

---

## PostgreSQL port conflict (5432)

**Symptom:** `password authentication failed for user "postgres"` on `localhost:5432`.

**Cause:** A **local** PostgreSQL instance listens on 5432; Docker db is on **5433**.

**Fix:** Ensure `.env` uses:

```
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5433/support
```

Verify Docker:

```powershell
docker compose ps
docker compose logs db
```

Reset volume only if credentials are stale (destroys local DB data):

```powershell
docker compose down -v
docker compose up -d db redis
uv run alembic upgrade head
```

---

## PostgreSQL password failed on 5433 (wrong container)

**Symptom:** `password authentication failed for user "postgres"` on `localhost:5433`. `docker compose ps` shows this project's `db` as healthy but only `5432/tcp` (no `0.0.0.0:5433->5432`).

**Cause:** Another Compose project already published host port **5433**. This app's Postgres never got a host mapping, so Alembic connected to the **other** database.

**Fix:** Pick a free host port and keep Compose + `DATABASE_URL` in sync:

```
POSTGRES_HOST_PORT=5434
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5434/support
```

Then recreate the mapping (does not require wiping the volume):

```powershell
docker compose up -d --wait --force-recreate db redis
docker compose port db 5432
uv run alembic upgrade head
```

---

## ProactorEventLoop (async scripts)

**Symptom:** `Psycopg cannot use the 'ProactorEventLoop' to run in async mode`.

**Where:** `scripts/seed_demo.py`, `scripts/ingest_kb.py`, or new async scripts run via `asyncio.run()`.

**Fix:** Use `SelectorEventLoop` on Windows (see `project-setup` skill). FastAPI/Uvicorn is unaffected.

---

## Checkpointer startup failure

**Symptom:** `CREATE INDEX CONCURRENTLY cannot run inside a transaction block` during app lifespan.

**Where:** `app/graph/workflow.py` → `create_checkpointer()`.

**Fix:** `AsyncConnectionPool(..., kwargs={"autocommit": True})`.

---

## PostgreSQL enum mismatch

**Symptom:** `invalid input value for enum ticket_status: "OPEN"`.

**Cause:** SQLAlchemy sends enum member **name** instead of **value**.

**Fix:** `values_callable=lambda x: [e.value for e in x]` on `Enum(StrEnum, ...)`.

---

## fastapi dev reload loop

**Symptom:** Repeated `WatchFiles detected changes in '.venv\Lib\site-packages\...'` and `KeyboardInterrupt`.

**Cause:** Hot-reload watches `.venv` while packages update (e.g. during `uv sync`).

**Fix:**

1. Stop the server before `uv sync`.
2. Or run without reload: `uv run fastapi run`.
3. Do not run bootstrap while `fastapi dev` is active.

---

## OpenAI / ingest failures

**Symptom:** HTTP errors during `ingest_kb.py`.

**Fix:** Set valid `OPENAI_API_KEY` in `.env`. Ingest calls the embeddings API.

---

## Docker not running

**Symptom:** `Cannot connect to the Docker daemon` or connection refused on 5433/6379.

**Fix:** Start Docker Desktop, then `docker compose up -d db redis`.

---

## MissingGreenlet on portal send (`greenlet_spawn` / `await_only`)

**Symptom:** Home composer (`Como podemos ajudar hoje?`) shows:

```json
{"detail":"Internal server error","error":"greenlet_spawn has not been called; can't call await_only() here."}
```

**Cause:** `POST /portal/conversations` mapped a freshly flushed `Ticket` with `ticket_to_response()`, which lazy-loads `ticket.customer` / `ticket.resolution` on `AsyncSession`.

**Fix:** After `flush`, `loaded = await ticket_service.get_ticket_or_404(session, ticket.id)` then `ticket_to_response(loaded)`. Same pattern as `close_ticket`. Full write-up: [runtime-invariants.md](runtime-invariants.md).

---

## Assistant reply appears then disappears (needs browser refresh)

**Symptom:** Portal/console shows the assistant bubble for ~1s, then the transcript reverts. Hard reload shows the persisted message.

**Cause:** SSE parser dropped `\r\n` frames / leftover `done` events, **and/or** Next.js re-rendered `/tickets/[id]` with stale `initialMessages`, wiping live state.

**Fix:** `web/hooks/use-chat-stream.ts` — normalize CRLF, flush the buffer on stream end, commit `done.answer`, keep a per-ticket live cache, merge server history additively. Do not `setMessages(initial)` on remount. Details: [runtime-invariants.md](runtime-invariants.md). Then invoke **realtime-chat**.

---

## SSE `/events` reconnects every ~15 seconds

**Symptom:** Next.js logs `GET /api/support/tickets/{id}/events 200 in 15.1s` in a loop. Live fan-out (console watching a portal chat) misses turns.

**Cause:** `asyncio.wait_for` on `pubsub.listen()` cancels the iterator after `CHAT_STREAM_HEARTBEAT_SECONDS`.

**Fix:** `subscribe_ticket_events` must use `pubsub.get_message(ignore_subscribe_messages=True, timeout=idle_timeout)` and yield a heartbeat when the result is `None`. Restart `scripts/run_api.py` after this backend change (no reload).

---

## Duplicate assistant bubbles (same text twice or glued)

**Symptom:** One customer turn shows the identical reply two or three times, sometimes concatenated without a newline.

**Cause:** Complete node `AIMessage` streamed as a `token`, leftover draft upserted after `done`, and/or EventSource replaying the POST events.

**Fix:** `_token_text` accepts only `*Chunk` types; clear `draftRef` on `done`; ignore EventSource while POST is in flight. Details: [runtime-invariants.md](runtime-invariants.md) §2d. Then invoke **realtime-chat**.

---

## `Escalation reason:` appears in the customer chat

**Symptom:** Internal label plus a copy of the same paragraph.

**Cause:** Escalation concatenated the interrupt reason into `draft_answer`.

**Fix:** Customer text stays in `draft_answer`; reason stays on the interrupt payload. `sanitize_customer_answer` is the persist safety net. Details: [runtime-invariants.md](runtime-invariants.md) §3.

---

## Human console reply appears twice

**Symptom:** Specialist message is shown twice (often one `human_agent` + one `assistant` with the same body).

**Cause:** `done.answer` or `persist_graph_result` copied the already-saved `HUMAN_AGENT` row.

**Fix:** `should_persist_assistant_message`; empty `done.answer` when the graph is not interrupted; hook fingerprints `assistant`/`human_agent` together. Details: [runtime-invariants.md](runtime-invariants.md) §2e.
