# TechStore Support — Agent Guide

Guide for Cursor agents working on this repository. Read this file first for context; rules in `.cursor/rules/` enforce conventions automatically.

## Project overview

Agent-centric **TechStore Support**: a **supervisor** classifies ticket intent, delegates to **domain agents** (billing, logistics, account), lets agents call **authorized tools** and **RAG** over a knowledge base, and **escalates to humans** when automation cannot resolve the case. The merchant is **TechStore**.

**Repository:** `AI-Customer-Support-Platform-With-Langgraph`  
**Backend package:** `app/` (Python / FastAPI).  
**Frontend:** Next.js App Router in [`web/`](web/) (Customer Portal + Support Console). Never put Next.js inside the Python `app/` package.

## Tech stack

| Area | Technology |
|------|------------|
| Backend | Python, FastAPI, Pydantic, Uvicorn |
| Agent orchestration | LangGraph (`StateGraph`, supervisor pattern) |
| LLM | API provider (OpenAI-compatible; configured via env) |
| RAG | PostgreSQL + pgvector |
| Persistence | PostgreSQL |
| Cache | Redis |
| Observability | OpenTelemetry, Langfuse |
| Testing | pytest, evaluation datasets |
| Infrastructure | Docker, Docker Compose, GitHub Actions |
| Frontend | Next.js 16.3 + React (App Router in `web/`) — `vercel-react-best-practices`; verify runtime with `next-dev-loop` |

## Directory structure

```
app/
├── api/
│   ├── routes/          # tickets.py, portal.py, health.py
│   └── dependencies.py  # auth, DB, graph, Redis, customer identity
├── agents/              # supervisor, billing, logistics, account, escalation, tool_loop, prompts
├── graph/               # state, nodes, edges, workflow
├── tools/               # billing/, logistics/, account/, escalation/, knowledge_base/
├── policies/            # deterministic policy engine (yaml + rules)
├── synthetic/           # TechStore world generator
├── retrieval/           # embeddings, retriever, reranker
├── security/            # authentication, authorization, permissions, guardrails, customer_identity
├── evaluation/          # datasets/, evaluators.py, metrics.py
├── observability/       # logging, tracing, metrics
├── models/              # ticket, ticket_message, customer, order, payment, shipment, refund, ...
├── services/            # ticket listing, graph runner, analytics, chat_bus
└── config.py

web/                     # Next.js Customer Portal + Support Console
tests/                   # unit/, integration/, evaluation/
data/company/            # company.yaml world model
data/fixtures/           # SCN-* evaluation fixtures
data/knowledge_base/     # policies, procedures, faq (RAG documents only)
docker/                  # container assets
scripts/                 # generate_data.py, seed_demo.py, ingest_kb.py
```

**Do not** introduce alternate Python layouts (`services/`, `graphs/`, `api/routers/`, `schemas/` as top-level packages) unless the team explicitly changes this map. The Next.js UI lives in **`web/`**, a sibling of the Python `app/` package.

## Cursor rules

| Rule | Scope | Purpose |
|------|-------|---------|
| `ai-engineer-standards.mdc` | Always | Python, stack, architecture, skill order |
| `ai-engineer-components.mdc` | `app/**`, `tests/**` | Layer map, LangGraph, API, RAG, testing |
| `frontend-next.mdc` | `*.tsx`, `*.jsx`, `web/**`, `frontend/**` | Next.js/React — load Vercel + next-dev-loop skills |

## Skills

Read the matching skill **before** implementing in that domain. This file is the project agent guide; do not confuse it with `.agents/skills/vercel-react-best-practices/AGENTS.md`.

**Where skills live**

| Scope | Path | Notes |
|-------|------|--------|
| Process + stack (CLI lockfile) | `.agents/skills/` | Installed via `npx skills add`; hashes in `skills-lock.json` |
| Domain (this product) | `.cursor/skills/` | Hand-authored: `project-setup`, `synthetic-data`, `synthetic-policies`, `company-architecture`, `realtime-chat`, `skill-creator` |

Two layers. **Process** (Matt) specifies and ships work. **Domain + stack** implement TechStore Support. Map of the process layer: `ask-matt`. Tracker, labels, and `CONTEXT.md` layout: `docs/agents/`.

### Process (idea → ship)

| Skill | Invoke when |
|-------|-------------|
| **grill-with-docs** | Sharpening an idea in this repo (writes `CONTEXT.md` / ADRs). Prefer this over `grill-me`. |
| **to-spec** / **to-tickets** | Multi-session build: spec first, then tracer-bullet tickets with blockers. |
| **implement** | Building a ticket or spec. Drives `tdd` at the seams below, then `code-review`. Commit only when the user asks. |
| **tdd** | Red-green at the seams in **Testing strategy**: unit (mocked LLM/DB), integration (test DB). Evaluation datasets are not the red-green loop. |
| **triage** | Incoming GitHub issues this session did not create. Tickets from `to-tickets` are already agent-ready. |
| **diagnosing-bugs** | Hard / intermittent bugs. Get a tight red loop before theorising. |

### Domain (TechStore Support)

| Skill | Location | Invoke when |
|-------|----------|-------------|
| **project-setup** | `.cursor/skills/project-setup/` | Clone, bootstrap, `.env`/Docker/ports, Windows, migrations, seed, ingest, API start, portal `greenlet_spawn`, chat reply that vanishes until F5, `/events` reconnecting every ~15s, duplicated chat bubbles, `Escalation reason:` in the transcript, human reply appearing twice. Details: `references/runtime-invariants.md`. |
| **synthetic-data** | `.cursor/skills/synthetic-data/` | Operational seed: `company.yaml`, generator, coherent FKs, `SCN-*` anomalies. Facts go to PostgreSQL, never to RAG. |
| **synthetic-policies** | `.cursor/skills/synthetic-policies/` | Policy v1.0: yaml constants, KB split, `app/policies/` mapping. |
| **company-architecture** | `.cursor/skills/company-architecture/` | Three sources (facts / policy engine / RAG documents), scoped tools, evals, security tests. The Assistant does not create Tickets (ADR-0007). |
| **realtime-chat** | `.cursor/skills/realtime-chat/` | Portal email login, `ticket_messages`, SSE + Redis, console inbox, Takeover, identity-first prompts. No WebSockets or product MCP. |

### Stack (when implementing a layer)

For this repo, `ecosystem-primer` selects **LangGraph** (custom control flow + HITL). Observability is **Langfuse**, not LangSmith.

| Skill | Location | Invoke when |
|-------|----------|-------------|
| **ecosystem-primer** | `.agents/skills/ecosystem-primer/` | First for LangChain/LangGraph work — then load the LangGraph skill below, not a new harness. |
| **langgraph-docs** | `.agents/skills/langgraph-docs/` | Graph design, supervisor + workers, live docs. |
| **langgraph-human-in-the-loop** | `.agents/skills/langgraph-human-in-the-loop/` | `interrupt()` / `Command(resume=...)` for Escalation. |
| **langgraph-persistence** | `.agents/skills/langgraph-persistence/` | Checkpointer, `thread_id`. This app uses `AsyncPostgresSaver` with `autocommit=True`. |
| **fastapi** | `.agents/skills/fastapi/` | Routes, `Depends`, Pydantic, SSE. Chat transport still goes through `realtime-chat`. The UI lives in `web/`; skip `app.frontend()`. |
| **langfuse** | `.agents/skills/langfuse/` | Traces, scores, datasets, prompt debugging. Env: `LANGFUSE_HOST`. |
| **vercel-react-best-practices** | `.agents/skills/vercel-react-best-practices/` | React/Next.js in `web/` — load matching `rules/` files only. |
| **next-dev-loop** | `.agents/skills/next-dev-loop/` | After UI edits, with `next dev` running — runtime check, not type-check alone. |
| **skill-creator** | `.cursor/skills/skill-creator/` | New or improved project skills. |

**Graph, retrieval, and deploy live in this package.** Agents: `StateGraph` supervisor in `app/graph/` + `app/agents/`. Retrieval: `app/retrieval/` + pgvector (`KnowledgeRetriever`). HTTP entry: FastAPI. Local/prod-like run: `docker-compose.yml` + `uv run fastapi dev`. There is no `langgraph.json`.

### Recommended skill order by task

0. **Unclear idea / new feature in this repo** → `grill-with-docs` (then `implement`, or `to-spec` → `to-tickets` if multi-session)
1. **New clone / env error / bootstrap / infra** → `project-setup`
2. **Synthetic company data / seed / anomalies / `generate_data.py`** → `synthetic-data` (after `project-setup` if DB/migrations are involved)
3. **Policy yaml / KB / engine sync** → `synthetic-policies` → `company-architecture`
4. **Scoped tools, evals, three-source changes** → `company-architecture` → then stack skills below
5. **Live chat / portal email login / console inbox / SSE** → `realtime-chat` → `fastapi` (SSE) → `langgraph-docs` + `langgraph-human-in-the-loop`
6. **New agent or graph feature** → `ecosystem-primer` → `langgraph-docs` → `ai-engineer-components` rule
7. **New API endpoint** → `fastapi` → `ai-engineer-components` rule
8. **RAG / retrieval** → extend `app/retrieval/` — documents only, never operational rows (`company-architecture`)
9. **Observability** → `langfuse` + `app/observability/`
10. **Evaluations** → `company-architecture` (case schema) → `app/evaluation/` + Langfuse datasets; pytest in `tests/evaluation/`
11. **Docker / deploy** → `docker-compose.yml` (graph is served from FastAPI)
12. **React / Next.js UI** → `vercel-react-best-practices` (matching `rules/*.md`) → with `next dev` running, `next-dev-loop`
13. **New or improved Cursor skill** → `skill-creator`

## Development conventions

### API layer

* Entry: `app` instance; routes in `app/api/routes/`.
* Thin handlers: validate → call graph or service logic → map to response DTO.
* Use `Annotated` + `Depends` for all injections.
* Prefer `fastapi dev` with entrypoint in `pyproject.toml` when configured.

### Agent layer

* **Supervisor** (`app/agents/supervisor.py`): intent classification and routing.
* **Workers:** billing, logistics, account — each owns domain tools only. Shared identity + style prompts: `app/agents/prompts.py`.
* **Escalation** (`app/agents/escalation.py`): human handoff. `draft_answer` is customer-facing only; `Escalation reason` stays on the interrupt payload.
* Graph assembly: `app/graph/workflow.py` imports nodes from `nodes.py` and edges from `edges.py`. First worker-facing node after guardrails: `load_customer_context`.
* Chat persistence: `ticket_messages`. Live fan-out: `app/services/chat_bus.py` (Redis `ticket:{id}:events`). SSE write path: `POST /tickets/{id}/messages`. Passive: `GET /tickets/{id}/events`.

### Security

* Authenticate in `app/security/authentication.py`; authorize per route/tool in `authorization.py` / `permissions.py`.
* Portal customer identity: `app/security/customer_identity.py` via `X-Customer-Email` (existing customer only).
* Apply `guardrails.py` on user input and model output before tools run or responses return (`sanitize_customer_answer` / `normalize_markdown` on assistant text).

### Data & RAG

* Models: `app/models/` — tickets, ticket_messages, customers, orders, resolutions.
* Vectors: pgvector in PostgreSQL; embedding and search in `app/retrieval/`.
* Static KB files: `data/knowledge_base/`.

### Observability

* Structured logging: `app/observability/logging.py`.
* OTel: `app/observability/tracing.py` — propagate context into graph invocations.
* Langfuse: trace LLM calls, tool runs, and evaluation runs; link traces to `ticket_id` when possible.

### Frontend (`web/`)

* Next.js 16.3 App Router + React. FastAPI remains the API and graph entry.
* Browser clients talk to `web/app/api/support/[...path]` (BFF). The BFF injects `X-API-Key` from `SUPPORT_API_KEY` and `X-Customer-Email` from the `portal_session` cookie — never `NEXT_PUBLIC_`.
* Customer Portal: `/portal/login` (email), `/` (live chat home), `/tickets/[id]` (thread + SSE).
* Support Console: `/console/inbox` (live conversations), `/console/inbox/[id]` (takeover), `/console/tickets`, `/console/analytics`. Cookie login at `/login`. `/console/escalations` redirects to the inbox filter.
* Write/review UI with `vercel-react-best-practices` (load only the matching `rules/*.md`). Chat work: also read `realtime-chat`.
* After edits, if `next dev` is running, verify with `next-dev-loop` — not compile/type-check alone. Playwright MCP (user) is allowed; `.cursor/mcp.json` stays empty.

## Environment variables (typical)

Copy from `.env.example` when present. Never commit secrets.

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL (app + pgvector). **Local host:** `localhost:${POSTGRES_HOST_PORT:-5433}` (Docker maps that port to `db:5432` to avoid conflict with a local Postgres on 5432) |
| `POSTGRES_HOST_PORT` | Host port published by Compose for Postgres (default `5433`). Must match the port in `DATABASE_URL` |
| `REDIS_URL` | Cache + chat pub/sub |
| `OPENAI_API_KEY` (or provider equivalent) | LLM + embeddings |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` | Langfuse |
| OTel exporter vars | OpenTelemetry backend |
| `CORS_ORIGINS` | Optional comma-separated browser origins (empty when using the Next.js BFF) |
| `CHAT_STREAM_HEARTBEAT_SECONDS` | SSE heartbeat interval (default 15) |
| `PORTAL_ALLOW_UNKNOWN_EMAIL` | Must stay `0` — unknown portal emails must not create customers |

Frontend (`web/.env.local`, copy from `web/.env.example`):

| Variable | Purpose |
|----------|---------|
| `SUPPORT_API_URL` | FastAPI base URL (`http://localhost:8000` locally, `http://api:8000` in Compose) |
| `SUPPORT_API_KEY` | Server-only API key matching `API_KEYS` |
| `CONSOLE_PASSWORD` | Support Console login |
| `PORTAL_SESSION_SECRET` | HMAC secret for the customer `portal_session` cookie |

## Demo portal logins (after `--profile demo --seed 42`)

Seed emails are realistic and unique. Unknown emails are rejected at `/portal/session`.

* `demo@test.com.br` — Demo Tester, 10 pedidos / 10 casos manuais (`SCN-DEMO-01` … `SCN-DEMO-10`). Roteiro: `data/fixtures/demo_manual_tests.md`
* `ana.costa@nexamail.com` — Ana Costa, double charge (`SCN-DOUBLE-PAY-001`), one order
* `pedro.lima@outlook.com` — delayed shipment
* `rafaela.fernandes@uol.com.br` — delivered but missing
* `nicolas.dias@outlook.com` — high-value refund

Full mapping: `data/fixtures/demo_logins.json`.

## Local development

Read **`project-setup`** skill (`.cursor/skills/project-setup/`) for the full bootstrap and troubleshooting guide.

### Quick path (Windows)

```powershell
Copy-Item .env.example .env   # set OPENAI_API_KEY
.\scripts\bootstrap.ps1
uv run fastapi dev
# In another terminal: the Next.js UI
Copy-Item web\.env.example web\.env.local
cd web; npm install; npm run dev
```

### Quick path (Linux / macOS)

```bash
cp .env.example .env
export UV_LINK_MODE=copy
uv sync --link-mode=copy
docker compose up -d db redis
uv run alembic upgrade head
uv run python scripts/seed_demo.py
uv run python scripts/ingest_kb.py
uv run fastapi dev
# UI: cp web/.env.example web/.env.local && cd web && npm install && npm run dev
```

### Local dev invariants

* **Postgres host port:** `POSTGRES_HOST_PORT` (default `5433`) in `.env` / `.env.example`, kept in sync with `DATABASE_URL`; Docker internal `db:5432` for the `api` service only.
* **LangGraph checkpointer:** `AsyncConnectionPool` in `app/graph/workflow.py` must use `kwargs={"autocommit": True}` (migrations use `CREATE INDEX CONCURRENTLY`).
* **StrEnum + PostgreSQL:** SQLAlchemy `Enum` columns need `values_callable=lambda x: [e.value for e in x]` so DB receives `open` not `OPEN`.
* **Async scripts on Windows:** `scripts/seed_demo.py` and `scripts/ingest_kb.py` use `SelectorEventLoop` when `sys.platform == "win32"`. The API sets `WindowsSelectorEventLoopPolicy` in `app/main.py` so Uvicorn/psycopg async works.
* **Hot reload:** If `fastapi dev` reloads on `.venv` changes, use `uv run fastapi run` or stop `uv sync` while the server is running.
* **Async ORM DTOs:** After `flush` on a new `Ticket`, reload with `get_ticket_or_404` (selectinload) before `ticket_to_response` — lazy `ticket.customer` raises MissingGreenlet.
* **Live chat UI:** `web/hooks/use-chat-stream.ts` must keep assistant turns without a browser refresh (CRLF SSE parse, `done.answer` fallback, per-ticket live cache) **and** must not duplicate them (chunk-only tokens, no leftover draft after `done`, fingerprint `assistant`+`human_agent`). Redis fan-out uses `get_message(timeout=)`, not `wait_for(listen())`. Human console replies persist once as `human_agent`.

## Commands

```bash
# Local API (once pyproject.toml entrypoint exists)
fastapi dev

# Tests
pytest tests/unit
pytest tests/integration
pytest tests/evaluation

# Frontend
cd web
npm run dev          # http://localhost:3000
npm run build
npm run typecheck
```

## Testing strategy

| Layer | Location | Focus |
|-------|----------|--------|
| Unit | `tests/unit/` | Tools, nodes, guardrails, retriever (mocked LLM/DB) |
| Integration | `tests/integration/` | API + graph end-to-end with test DB |
| Evaluation | `tests/evaluation/` | Dataset runs, regression on agent quality metrics |

Evaluation code lives in `app/evaluation/`; pytest wrappers in `tests/evaluation/`.

## What agents should not do

* Hardcode API keys, model names, or connection strings.
* Put SQL commits or HTTP calls directly inside graph nodes — use tools and injected dependencies.
* Skip guardrails or permission checks for tool execution.
* Bypass supervisor routing for domain-specific logic.
* Use `print` for operational logging.
* Implement from memory for Langfuse, LangGraph, FastAPI, or Next.js APIs — use skills and live docs.
* Treat TypeScript compile or type-check as sufficient verification of a running Next.js app — use `next-dev-loop` when `next dev` is up.
* Lazy-load SQLAlchemy relationships on `AsyncSession` after `flush` (`ticket.customer`) — MissingGreenlet.
* Reset live chat state from stale Server Component `initialMessages`, or heartbeat Redis SSE by cancelling `pubsub.listen()`.
* Stream complete node `AIMessage`s as SSE tokens, append leftover draft after `done`, or show `Escalation reason:` to the customer.
* Persist or render a human console reply a second time as `assistant`.

## Language

* **Code and docs in repo:** English.
* **User communication:** Portuguese (per team preference in rules).

## Agent skills

### Issue tracker

Issues live in this repo's GitHub Issues (via `gh`). See `docs/agents/issue-tracker.md`.

### Triage labels

Canonical roles map 1:1 to tracker labels (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` plus `docs/adr/` at the repo root. See `docs/agents/domain.md`.
