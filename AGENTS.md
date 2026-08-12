# AI Customer Support Platform — Agent Guide

Guide for Cursor agents working on this repository. Read this file first for context; rules in `.cursor/rules/` enforce conventions automatically.

## Project overview

Agent-centric customer support platform: a **supervisor** classifies ticket intent, delegates to **domain agents** (billing, logistics, account), lets agents call **authorized tools** and **RAG** over a knowledge base, and **escalates to humans** when automation cannot resolve the case.

**Repository:** `AI-Customer-Support-Platform-With-Langgraph`  
**App package:** `app/` (Python backend only — no frontend in current scope)

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

## Directory structure

```
app/
├── api/
│   ├── routes/          # tickets.py, health.py
│   └── dependencies.py  # auth, DB, graph, Redis
├── agents/              # supervisor, billing, logistics, account, escalation
├── graph/               # state, nodes, edges, workflow
├── tools/               # billing/, logistics/, account/, knowledge_base/
├── retrieval/           # embeddings, retriever, reranker
├── security/            # authentication, authorization, permissions, guardrails
├── evaluation/          # datasets/, evaluators.py, metrics.py
├── observability/       # logging, tracing, metrics
├── models/              # ticket, customer, resolution
└── config.py

tests/                   # unit/, integration/, evaluation/
data/knowledge_base/     # source documents for RAG
docker/                  # container assets
scripts/                 # dev and ops helpers
```

**Do not** introduce alternate layouts (`services/`, `graphs/`, `api/routers/`, `schemas/` as top-level packages) unless the team explicitly changes this map.

## Cursor rules

| Rule | Scope | Purpose |
|------|-------|---------|
| `ai-engineer-standards.mdc` | Always | Python, stack, architecture, skill order |
| `ai-engineer-components.mdc` | `app/**`, `tests/**` | Layer map, LangGraph, API, RAG, testing |

## Installed skills — when to invoke

Read the skill file **before** implementing in that domain. Skills under `.agents/skills/` are project-local; Langfuse is enabled via Cursor plugin.

| Skill | Location | Invoke when |
|-------|----------|-------------|
| **ecosystem-primer** | `.agents/skills/ecosystem-primer/` | **First** for any LangChain/LangGraph/agent work — framework choice and next skill |
| **fastapi** | `.agents/skills/fastapi/` | Routes, dependencies, Pydantic models, SSE streaming |
| **langgraph-docs** | `.agents/skills/langgraph-docs/` | Graph design, multi-agent flows, HITL, checkpoints — fetch live docs via skill workflow |
| **langgraph-cli** | `.agents/skills/langgraph-cli/` | `langgraph.json`, `langgraph dev/build/up`, local Docker lifecycle |
| **langfuse** | Cursor plugin (`langfuse` enabled in `.cursor/settings.json`) | Tracing, scores, datasets, prompt management, trace debugging |
| **skill-creator** | `.cursor/skills/skill-creator/` | Creating or benchmarking new Cursor skills for this project |

### Recommended skill order by task

1. **New agent or graph feature** → `ecosystem-primer` → `langgraph-docs` → `ai-engineer-components` rule
2. **New API endpoint** → `fastapi` → `ai-engineer-components` rule
3. **RAG / retrieval** → `ecosystem-primer` (RAG section) → implement in `app/retrieval/`
4. **Observability** → Langfuse skill + `app/observability/`
5. **Evaluations** → `app/evaluation/` + Langfuse datasets; pytest in `tests/evaluation/`
6. **Docker / deploy** → `langgraph-cli` if using LangGraph Platform; otherwise `docker-compose.yml`

## Development conventions

### API layer

* Entry: `app` instance; routes in `app/api/routes/`.
* Thin handlers: validate → call graph or service logic → map to response DTO.
* Use `Annotated` + `Depends` for all injections.
* Prefer `fastapi dev` with entrypoint in `pyproject.toml` when configured.

### Agent layer

* **Supervisor** (`app/agents/supervisor.py`): intent classification and routing.
* **Workers:** billing, logistics, account — each owns domain tools only.
* **Escalation** (`app/agents/escalation.py`): human handoff criteria and ticket state updates.
* Graph assembly: `app/graph/workflow.py` imports nodes from `nodes.py` and edges from `edges.py`.

### Security

* Authenticate in `app/security/authentication.py`; authorize per route/tool in `authorization.py` / `permissions.py`.
* Apply `guardrails.py` on user input and model output before tools run or responses return.

### Data & RAG

* Models: `app/models/` — tickets, customers, resolutions.
* Vectors: pgvector in PostgreSQL; embedding and search in `app/retrieval/`.
* Static KB files: `data/knowledge_base/`.

### Observability

* Structured logging: `app/observability/logging.py`.
* OTel: `app/observability/tracing.py` — propagate context into graph invocations.
* Langfuse: trace LLM calls, tool runs, and evaluation runs; link traces to `ticket_id` when possible.

## Environment variables (typical)

Copy from `.env.example` when present. Never commit secrets.

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL (app + pgvector) |
| `REDIS_URL` | Cache |
| `OPENAI_API_KEY` (or provider equivalent) | LLM + embeddings |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` | Langfuse |
| OTel exporter vars | OpenTelemetry backend |

LangSmith vars (`LANGSMITH_*`) apply when using LangGraph Platform or LangSmith tracing alongside Langfuse.

## Commands

```bash
# Local API (once pyproject.toml entrypoint exists)
fastapi dev

# Tests
pytest tests/unit
pytest tests/integration
pytest tests/evaluation

# Docker
docker compose up --build
```

For LangGraph CLI workflows, see `langgraph-cli` skill (`langgraph dev`, `langgraph up`, etc.).

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
* Implement from memory for Langfuse or LangGraph APIs — use skills and live docs.

## Language

* **Code and docs in repo:** English.
* **User communication:** Portuguese (per team preference in rules).
