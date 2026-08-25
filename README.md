# AI Customer Support Platform

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?style=flat-square&logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![Next.js](https://img.shields.io/badge/Next.js-000?style=flat-square&logo=next.js&logoColor=white)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io/)

Production-oriented customer support for **NexaCommerce**: a **supervisor** routes tickets to domain workers that look up **operational facts in PostgreSQL**, retrieve **policies via RAG**, and enforce **deterministic rules** before any refund or cancellation. The LLM does not invent order state.

[Overview](#overview) · [Features](#features) · [Architecture](#architecture) · [Screenshots](#screenshots) · [Getting started](#getting-started) · [Demo scenarios](#demo-scenarios) · [API](#api) · [Project structure](#project-structure) · [Testing](#testing) · [Deployment](#deployment)

![Live support chat — AI agent answering a shipping inquiry](Images/chat-interação-assistente.png)

## Overview

This is not a FAQ chatbot. It is an agent-centric support platform where:

- **PostgreSQL** holds customers, orders, payments, shipments, and tickets — the source of truth for facts.
- **RAG (pgvector)** indexes policy documents, procedures, and FAQs from `data/knowledge_base/`.
- **Policy engine** (`app/policies/`, `data/company/company.yaml`) evaluates refund windows, approval thresholds, and shipping rules in Python before the model acts.

Tools are scoped to the ticket customer. Critical numbers (30-day window, BRL 1000 approval) live in `company.yaml` and are never left to the LLM alone.

The stack includes a **Customer Portal** (email login + live chat) and a **Support Console** (inbox, human takeover, tickets, analytics). The Next.js UI talks to FastAPI through a BFF so API keys never reach the browser.

## Features

- **Multi-agent orchestration** — LangGraph supervisor delegates to billing, logistics, and account workers.
- **Three knowledge sources** — operational DB, deterministic policies, and RAG over static documents.
- **Scoped tools** — `get_order`, `get_payments`, `get_shipment`, `check_refund_eligibility`, and more, bound to the authenticated customer.
- **Human-in-the-loop** — escalation with console inbox takeover; human replies persist as `human_agent`.
- **Live chat** — SSE token streaming, Redis pub/sub fan-out, `ticket_messages` persistence.
- **Synthetic NexaCommerce world** — reproducible demo data with labeled anomalies (`SCN-*`) for evals.
- **Observability** — OpenTelemetry traces and Langfuse for LLM/tool runs.
- **Evaluation harness** — pytest suites plus dataset metrics in `app/evaluation/`.

## Architecture

```mermaid
flowchart TD
    Browser[Next.js BFF + UI] --> API[FastAPI Routes]
    API --> Guard[Guardrails]
    Guard --> Graph[LangGraph Workflow]
    Graph --> Supervisor[Supervisor]
    Supervisor --> Billing[Billing Agent]
    Supervisor --> Logistics[Logistics Agent]
    Supervisor --> Account[Account Agent]
    Supervisor --> Escalation[Escalation Agent]
    Billing --> Tools[Scoped Tools]
    Billing --> RAG[pgvector RAG]
    Billing --> Policy[Policy Engine]
    Logistics --> Tools
    Account --> Tools
    Tools --> DB[(PostgreSQL facts)]
    RAG --> KB[Policy documents]
    Policy --> YAML[company.yaml]
    API --> Redis[(Redis cache + pub/sub)]
```

| Layer | Technology |
|-------|------------|
| API | FastAPI, Pydantic, Uvicorn |
| Agents | LangGraph (supervisor + domain workers) |
| LLM | OpenAI-compatible (configured via env) |
| RAG | PostgreSQL + pgvector |
| Cache / live events | Redis |
| Observability | OpenTelemetry, Langfuse |
| Frontend | Next.js 16 (Customer Portal + Support Console) |
| Infrastructure | Docker, Docker Compose, GitHub Actions |

## Screenshots

### Customer Portal

Email-only login — unknown addresses are rejected; customers are never created from the portal.

![Customer portal login](Images/interface-suporte-cliente.png)

Live chat with streaming assistant replies grounded in real order data.

![Support chat with AI agent](Images/chat-interação-assistente.png)

When automation cannot resolve the case, the ticket escalates and a human specialist continues the thread.

![Escalation to human agent](Images/chat-interação-assistente-para-humano.png)

![Human agent reply in the portal](Images/chat-human-response.png)

Customers can mark a conversation as resolved when the issue is closed.

![Resolved conversation](Images/resolvido.png)

### Support Console

Dark-themed console for the support team: inbox, ticket management, and analytics.

![Support console](Images/interface-suporte-console.png)

![Live inbox with escalated conversations](Images/interface-inbox.png)

![Human takeover in the console](Images/interface-human-interation.png)

![Ticket list](Images/interface-tickets.png)

![Analytics — escalation rate, intent mix, tool latency](Images/interface-analytics.png)

![Console resources overview](Images/interface-console-recourses.png)

### API, data stores, and deployment

![API health check](Images/health-check.png)

![FastAPI running locally](Images/terminal-api.png)

![Next.js frontend dev server](Images/terminal-frontend.png)

![PostgreSQL with pgvector](Images/database-postgree.png)

![Redis (Valkey) for cache and chat pub/sub](Images/database-valkey-redis.png)

![Deployed components on App Platform](Images/deploy-components.png)

## Getting started

### Prerequisites

- Python 3.12 (managed via [uv](https://docs.astral.sh/uv/))
- Node.js 20+ (for the Next.js UI)
- Docker and Docker Compose
- OpenAI API key

### Backend setup

```bash
# Copy environment file
cp .env.example .env
# Edit .env — set OPENAI_API_KEY

# Bootstrap (Windows) — sets UV_LINK_MODE=copy to avoid hardlink errors
./scripts/bootstrap.ps1

# Or manually (Windows: always use copy link mode)
export UV_LINK_MODE=copy          # bash
# $env:UV_LINK_MODE = "copy"      # PowerShell
uv sync --link-mode=copy
docker compose up -d db redis
uv run alembic upgrade head
uv run python scripts/generate_data.py --profile demo --seed 42
uv run python scripts/ingest_kb.py
uv run fastapi dev
```

### Frontend setup

```bash
cp web/.env.example web/.env.local
cd web
npm install
npm run dev
```

| URL | Purpose |
|-----|---------|
| http://localhost:3000 | Customer portal |
| http://localhost:3000/portal/login | Email login |
| http://localhost:3000/login | Support console (default password `console`) |
| http://localhost:3000/console/inbox | Live inbox |
| http://localhost:8000/docs | OpenAPI docs |

> [!TIP]
> The UI proxies API calls through `/api/support/*`. `SUPPORT_API_KEY` and `X-Customer-Email` are injected server-side — never expose them with `NEXT_PUBLIC_`.

> [!NOTE]
> **Database URL:** local development uses PostgreSQL on host port **5433** (`localhost:5433`) so Docker does not conflict with a local Postgres on 5432. If 5433 is taken, set `POSTGRES_HOST_PORT` and `DATABASE_URL` together. See `.env.example`.

### Windows notes

On Windows, `uv` may fail with **os error 396** (*cloud operation incompatible with hardlinks*) when the project, `.venv`, or `%LOCALAPPDATA%\uv` cache is on a cloud-synced path. The bootstrap script sets `UV_LINK_MODE=copy` and uses `C:\uv-cache` by default when `UV_CACHE_DIR` is unset.

If problems persist:

- Prefer a local path such as `C:\dev\your-project` (outside OneDrive).
- Or set `UV_PROJECT_ENVIRONMENT=C:\venvs\your-project` so `.venv` is not inside a synced folder.
- Rebuild: `Remove-Item -Recurse -Force .venv` then `uv sync --link-mode=copy`.

## Demo scenarios

After `generate_data.py --profile demo --seed 42`, sign in at `/portal/login`:

| Email | Name | Typical scenario |
|-------|------|------------------|
| `demo@test.com.br` | Demo Tester | **10 orders** — manual test script in [`data/fixtures/demo_manual_tests.md`](data/fixtures/demo_manual_tests.md) |
| `ana.costa@nexamail.com` | Ana Costa | Double charge (`SCN-DOUBLE-PAY-001`) |
| `pedro.lima@outlook.com` | Pedro Lima | Delayed shipment |
| `rafaela.fernandes@uol.com.br` | Rafaela Fernandes | Delivered but missing |
| `nicolas.dias@outlook.com` | Nicolas Dias | High-value refund |

Full login list: [`data/fixtures/demo_logins.json`](data/fixtures/demo_logins.json).

The demo customer (`demo@test.com.br`) covers ten labeled scenarios — double payment, delayed shipment, refund outside window, high-value refund, and more. Each row in `demo_manual_tests.md` lists the order ID, suggested message, expected tools, and whether human escalation is expected.

## API

All endpoints require the `X-API-Key` header (default: `dev-key` from `.env.example`).

```bash
# Health check
curl http://localhost:8000/health

# Create ticket
curl -X POST http://localhost:8000/tickets \
  -H "X-API-Key: dev-key" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_email": "customer@example.com",
    "customer_name": "Customer",
    "subject": "Refund request",
    "description": "I was charged twice for INV-1001"
  }'

# Resolve ticket (chat turn)
curl -X POST http://localhost:8000/tickets/{ticket_id}/resolve \
  -H "X-API-Key: dev-key" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Please refund duplicate charge on INV-1001"}]}'
```

Portal chat uses `POST /tickets/{id}/messages` and `GET /tickets/{id}/events` (SSE). See [AGENTS.md](AGENTS.md) for the full API and agent layer map.

## Project structure

```
app/                  # FastAPI + LangGraph backend
├── api/routes/       # tickets, portal, health
├── agents/           # supervisor, billing, logistics, account, escalation
├── graph/            # state, nodes, edges, workflow
├── tools/            # scoped domain tools
├── policies/         # deterministic policy engine
├── retrieval/        # embeddings, pgvector retriever
├── models/           # SQLAlchemy models
├── services/         # ticket listing, graph runner, chat_bus, analytics
└── evaluation/       # datasets, evaluators, metrics

web/                  # Next.js Customer Portal + Support Console
data/
├── company/          # company.yaml world model
├── fixtures/         # SCN-* eval fixtures, demo logins
└── knowledge_base/   # RAG documents (policies, procedures, FAQ)

scripts/              # generate_data, seed_demo, ingest_kb
tests/                # unit, integration, evaluation
```

Agent development guide and conventions: [AGENTS.md](AGENTS.md).

## Testing

```bash
uv run pytest tests/unit -v
uv run pytest tests/integration -v
uv run pytest tests/evaluation -v
```

Evaluation thresholds live in `app/evaluation/metrics.py` (intent accuracy, tool-call correctness, policy compliance, unauthorized-action rate = 0). Publish measured scores only after a real eval run.

## Synthetic data

```bash
uv run python scripts/generate_data.py --profile demo --seed 42
uv run python scripts/generate_data.py --profile v1 --seed 42 --replace
```

| Profile | Description |
|---------|-------------|
| `demo` | Local smoke — every anomaly kind |
| `v1` | 1000 customers / 3000 orders |
| `load` | Optional load-test scale |

Fixtures are written to `data/fixtures/scenarios.json`. Do not put order rows in the knowledge base.

## Deployment

Docker Compose runs the full stack locally (`db`, `redis`, `api`, `web`):

```bash
docker compose up -d
```

For cloud deployment, the platform typically splits into an API service, a Next.js web service, PostgreSQL (pgvector), Redis, and optional seed/ingest jobs — as shown in the App Platform overview above.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Postgres auth failed on port 5432 | Use `localhost:5433` in `DATABASE_URL` (Docker maps `5433:5432`) |
| Postgres auth failed on port 5433 | Another container owns 5433 — set `POSTGRES_HOST_PORT` and `DATABASE_URL` to a free port (e.g. 5434) |
| `ProactorEventLoop` in seed/ingest | Use latest `scripts/` — Windows needs `SelectorEventLoop` |
| API fails with `CREATE INDEX CONCURRENTLY` | Checkpointer pool needs `autocommit=True` in `app/graph/workflow.py` |
| `fastapi dev` reload loop on `.venv` | Use `uv run fastapi run` or stop `uv sync` while the server runs |
| Assistant reply only appears after F5 | See live-chat invariants in [AGENTS.md](AGENTS.md) and `.agents/skills/project-setup/` |
| Duplicated chat bubbles | Same — chunk-only SSE tokens, no leftover draft after `done` |

Full bootstrap and runtime guide: `.agents/skills/project-setup/`.

## Environment variables

See [.env.example](.env.example) and [`web/.env.example`](web/.env.example) for all options. Key variables:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL + pgvector (`localhost:5433` locally) |
| `REDIS_URL` | Cache + chat pub/sub |
| `OPENAI_API_KEY` | LLM + embeddings |
| `API_KEYS` | Semicolon-separated API keys with scopes |
| `LANGFUSE_*` | Optional tracing |
| `SUPPORT_API_URL` / `SUPPORT_API_KEY` | Next.js BFF → FastAPI (server-only) |
| `CONSOLE_PASSWORD` | Support console login |
| `PORTAL_SESSION_SECRET` | HMAC for customer session cookie |
