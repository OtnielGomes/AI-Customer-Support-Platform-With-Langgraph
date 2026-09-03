---
name: project-setup
description: "INVOKE FIRST for local development setup, bootstrap, environment configuration, Docker/PostgreSQL/Redis, Windows troubleshooting, and project-wide adjustments to this AI Customer Support Platform. Use when onboarding, fixing dev environment errors, changing ports or .env, running migrations/seed/ingest, starting FastAPI, or before any cross-cutting infra change. Also use when the user asks how to run, configure, or fix this repository. Trigger on portal 500 greenlet_spawn / await_only / MissingGreenlet, assistant reply that only appears after refresh, SSE /events reconnecting every ~15s, duplicated chat bubbles (same answer twice or concatenated), Escalation reason leaking to the customer, or a human console reply appearing twice."
compatibility: "Python 3.12, uv, Docker Compose, Windows or Linux. Requires .env from .env.example."
---

# Project Setup — AI Customer Support Platform

Canonical workflow for **creating**, **bootstrapping**, and **adjusting** this repository. Read `AGENTS.md` for the layer map; use this skill for **how to run and configure** the project.

## When to invoke

| Situation | Action |
|-----------|--------|
| First clone / new machine | Full bootstrap (below) |
| DB connection/auth errors | Check port 5433 vs local Postgres on 5432 |
| `ProactorEventLoop` / psycopg async errors | Windows event-loop fix (scripts) |
| `CREATE INDEX CONCURRENTLY` on startup | Checkpointer `autocommit=True` |
| `invalid input value for enum` | StrEnum `values_callable` on SQLAlchemy `Enum` |
| `fastapi dev` reload loop on `.venv` | Use `fastapi run` or stop `uv sync` while server runs |
| `greenlet_spawn` / `await_only` on portal send | Reload ticket with `selectinload` before `ticket_to_response` |
| Assistant reply flashes then vanishes (needs F5) | Live-chat cache + SSE parser; see runtime invariants |
| `GET /tickets/{id}/events` finishes every ~15s | Redis `get_message(timeout=)` — do not `wait_for` on `listen()` |
| Same assistant text twice / concatenated with no newline | Token filter + leftover draft; see runtime invariants §2d |
| Chat shows `Escalation reason:` | Internal handoff only; see runtime invariants §3 |
| Human console reply appears twice | Do not persist `done.answer` as assistant; see runtime invariants §2e |
| New feature in a layer | Bootstrap OK → invoke layer skill (`fastapi`, `langgraph-docs`, `realtime-chat`, etc.) |

## Skill order for changes

```
project-setup (this skill)     → env, Docker, bootstrap, infra + runtime invariants
synthetic-policies             → after KB/policy edits: ingest_kb + test_policy_docs_sync
realtime-chat                  → portal/console live chat, SSE, Redis fan-out
ecosystem-primer               → any LangGraph/agent work
langgraph-docs / fastapi / …   → layer-specific implementation
ai-engineer-components rule    → code patterns in app/ and tests/
```

---

## First-time setup

### 1. Prerequisites

- Python **3.12** (via [uv](https://docs.astral.sh/uv/))
- Docker Desktop (PostgreSQL + Redis)
- OpenAI API key

### 2. Environment

```powershell
Copy-Item .env.example .env
# Edit .env: OPENAI_API_KEY, optional Langfuse keys
```

| Variable | Local default | Notes |
|----------|---------------|-------|
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5433/support` | Host port **5433** by default (avoids conflict with local Postgres on 5432). Keep in sync with `POSTGRES_HOST_PORT` |
| `POSTGRES_HOST_PORT` | `5433` | Compose host mapping. Change together with `DATABASE_URL` if 5433 is already taken |
| `REDIS_URL` | `redis://localhost:6379/0` | |
| `API_KEYS` | `dev-key:read,write,billing:write` | Header: `X-API-Key: dev-key` |

Inside Docker Compose, the `api` service uses `db:5432` (internal network). Host dev uses `POSTGRES_HOST_PORT` (default **5433**).

### 3. Bootstrap (recommended)

```powershell
.\scripts\bootstrap.ps1
```

Steps performed: `uv sync` → Docker `db` + `redis` → Alembic migrations → `seed_demo.py --as-of today` → `ingest_kb.py`.

Order dates in a fresh seed are anchored at **today** (company timezone). CI and unit tests keep `simulation.clock: frozen` in `data/company/company.yaml`. To regenerate with a new anchor on an existing DB, use `generate_data.py --replace --as-of today`.

### 4. Start API

```powershell
uv run fastapi dev
```

- Docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

If hot-reload spams `WatchFiles detected changes in .venv`, use:

```powershell
uv run fastapi run
```

---

## Manual bootstrap (Linux / macOS / CI-style)

```bash
export UV_LINK_MODE=copy   # safe on synced filesystems
uv sync --link-mode=copy
docker compose up -d db redis
uv run alembic upgrade head
uv run python scripts/seed_demo.py --as-of today
uv run python scripts/ingest_kb.py
uv run fastapi dev
```

---

## Project conventions agents must preserve

### LangGraph checkpointer (`app/graph/workflow.py`)

`AsyncPostgresSaver.setup()` runs migrations with `CREATE INDEX CONCURRENTLY`, which **requires autocommit**:

```python
pool = AsyncConnectionPool(
    conninfo=settings.checkpoint_database_url(),
    max_size=10,
    open=False,
    kwargs={"autocommit": True},
)
```

Do not remove `autocommit=True` from the checkpointer pool.

### PostgreSQL `StrEnum` columns (`app/models/`)

SQLAlchemy must persist enum **values** (`open`), not names (`OPEN`):

```python
Enum(TicketStatus, name="ticket_status", values_callable=lambda x: [e.value for e in x])
```

Apply the same pattern to any new `StrEnum` mapped to PostgreSQL enums.

### Async CLI scripts (`scripts/*.py`)

On Windows, psycopg async requires `SelectorEventLoop`:

```python
if sys.platform == "win32":
    asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop)
else:
    asyncio.run(main())
```

Use this in any new `scripts/` entrypoint that calls async SQLAlchemy or psycopg.

### Docker host port

`docker-compose.yml` maps Postgres as `${POSTGRES_HOST_PORT:-5433}:5432`. If you change the host port, update **all** of:

- local `.env` (`POSTGRES_HOST_PORT` **and** the port in `DATABASE_URL`)
- `.env.example` / `app/config.py` only when changing the **default**

CI (GitHub Actions) may keep `5432` — that is isolated and fine.

### Async ORM + live chat (do not regress)

Read [references/runtime-invariants.md](references/runtime-invariants.md) before changing ticket DTOs, `POST /portal/conversations`, SSE parsers, or Redis subscribers.

| Invariant | Path |
|-----------|------|
| After `flush`, reload with `selectinload` before `ticket_to_response` | `app/api/routes/portal.py`, `app/services/ticket_service.py` |
| SSE frames: normalize `\r\n`, flush leftover on stream end, commit `done.answer` | `web/hooks/use-chat-stream.ts` |
| Stream **only** `AIMessageChunk` tokens; skip complete node `AIMessage` | `app/services/chat_service.py` `_token_text` |
| Do not append leftover draft after `done`; ignore EventSource while POST is in flight | `web/hooks/use-chat-stream.ts` |
| Never concatenate `Escalation reason:` into `draft_answer` | `app/agents/escalation.py`, `sanitize_customer_answer` |
| Human turn: persist `human_agent` once; skip identical assistant copy | `should_persist_assistant_message`, empty `done.answer` when not interrupted |
| Never replace live messages with stale RSC `initialMessages` | same hook — module cache, additive merge |
| Heartbeat via `pubsub.get_message(timeout=)`, never `wait_for(listen())` | `app/services/chat_bus.py` |

Chat feature work continues in **realtime-chat**. Python API started with `scripts/run_api.py` does **not** hot-reload — restart it after backend edits.

---

## Adjusting the project by layer

| Change type | Read first | Touch |
|-------------|------------|-------|
| API routes / DTOs | `fastapi` skill | `app/api/` |
| Graph / agents | `ecosystem-primer` → `langgraph-docs` | `app/graph/`, `app/agents/` |
| Tools | `ai-engineer-components` | `app/tools/<domain>/` |
| RAG | `ecosystem-primer` (RAG) | `app/retrieval/`, `data/knowledge_base/` |
| DB schema | Alembic | `migrations/`, `app/models/` |
| Env / ports / Docker | **this skill** | `.env.example`, `docker-compose.yml`, `scripts/` |
| Portal chat / SSE / Redis fan-out | **this skill** (invariants) → `realtime-chat` | `app/api/routes/portal.py`, `app/services/chat_*.py`, `web/hooks/use-chat-stream.ts` |
| Observability | Langfuse plugin skill | `app/observability/` |

After model changes: `uv run alembic revision --autogenerate -m "..."` then `uv run alembic upgrade head`.

After KB file changes: `uv run python scripts/ingest_kb.py`.

---

## Verification checklist

```powershell
docker compose ps                    # db + redis Up
uv run alembic current                 # migration head
uv run python scripts/seed_demo.py   # no errors
curl http://localhost:8000/health     # 200
```

---

## Troubleshooting

See [references/troubleshooting.md](references/troubleshooting.md) for Windows/Docker/uv fixes. See [references/runtime-invariants.md](references/runtime-invariants.md) for portal 500, chat UI wipe, duplicate bubbles, and escalation-reason leaks.

Quick reference:

| Error | Likely cause | Fix |
|-------|--------------|-----|
| Password auth failed for `postgres` on 5432 | Local Postgres, not Docker | Use port **5433** in `DATABASE_URL` |
| Password auth failed for `postgres` on 5433 | Another Compose project already bound 5433 | Set `POSTGRES_HOST_PORT` + `DATABASE_URL` to a free port |
| `ProactorEventLoop` | Windows + async psycopg in script | `SelectorEventLoop` in script `__main__` |
| `CREATE INDEX CONCURRENTLY` in transaction | Checkpointer pool without autocommit | `kwargs={"autocommit": True}` |
| `invalid input value for enum` | StrEnum name vs value | `values_callable` on `Enum()` |
| uv os error 396 (hardlinks) | OneDrive/cloud path | `UV_LINK_MODE=copy`, `C:\uv-cache` |
| Reload storm on `.venv` | `fastapi dev` + package install | `fastapi run` or stop sync during dev |
| `greenlet_spawn` / `await_only` | Lazy `ticket.customer` after flush | `get_ticket_or_404` then `ticket_to_response` |
| Assistant appears then vanishes | Stale RSC `initial` reset + SSE leftover | Live cache; flush SSE buffer; commit `done.answer` |
| `/events` 200 every ~15s | `wait_for` cancelled `listen()` | `pubsub.get_message(timeout=idle)` |
| Same answer twice / glued together | Complete `AIMessage` streamed as a token + leftover draft upsert | `_token_text` chunks only; clear draft on `done` |
| `Escalation reason:` in the bubble | `run_escalation_agent` concatenated reason into `draft_answer` | Keep reason on the interrupt payload only |
| Human reply duplicated | `done.answer` / persist copied `human_agent` as `assistant` | `should_persist_assistant_message`; fingerprint `agent:` |

---

## What not to do

- Do not commit `.env` or API keys.
- Do not map Docker Postgres back to host `5432` without checking for a local Postgres conflict.
- Do not add top-level packages (`services/`, `graphs/`, `api/routers/`) — see `AGENTS.md`.
- Do not bypass `scripts/bootstrap.ps1` conventions on Windows without setting `UV_LINK_MODE=copy`.
- Do not call `ticket_to_response` on a row that was only `flush`ed — reload with `selectinload` (MissingGreenlet).
- Do not reset chat `messages` from Server Component `initialMessages` on every render/remount.
- Do not use `asyncio.wait_for` on Redis `pubsub.listen()` for SSE heartbeats.
- Do not treat complete node `AIMessage`s as SSE `token`s, or upsert leftover draft after `done`.
- Do not put `Escalation reason:` (or other interrupt metadata) in customer-facing `draft_answer`.
- Do not persist or render a human console reply a second time as `assistant`.
