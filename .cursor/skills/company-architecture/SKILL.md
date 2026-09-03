---
name: company-architecture
description: "INVOKE when changing TechStore Support's three knowledge sources (PostgreSQL facts, deterministic policy engine, RAG documents), scoped domain tools, evaluation cases, or negative security tests. Use when the user asks to add or change a billing/logistics/account tool, check_refund_eligibility, policy engine wiring, KB layout vs yaml, or eval cases tied to SCN-*. Read synthetic-data first if schema or seed is missing; read synthetic-policies for policy v1.0 yaml/KB/engine sync. Do not use for Docker/bootstrap (project-setup), generating rows alone (synthetic-data), or live chat/SSE (realtime-chat)."
compatibility: "FastAPI, LangGraph, PostgreSQL/pgvector, existing app/ layout. Requires synthetic-data for operational tables. MCP is out of v1."
---

# TechStore company architecture

Keep TechStore Support as **a support system that operates inside TechStore**: transactional lookup, versioned policies, controlled actions, deterministic rules.

The FAQ-chatbot → three-source migration **already landed**. Do **not** recreate a top-level layout or re-run that migration. Adapt **this** `app/` package.

## Skill order

```
project-setup                     → DB, Alembic, Windows, ports
synthetic-data               → company.yaml, catalog, schema, generator, anomalies
synthetic-policies           → policy v1.0 → yaml constants, KB split, engine mapping
company-architecture (this)  → tools, policies, KB, graph, evals, security
realtime-chat                → email portal session, ticket_messages, SSE chat, console inbox
ecosystem-primer → langgraph-docs → graph/agent code
fastapi                           → new routes/DTOs
```

Historical why (not a to-do list): [references/gap-analysis.md](references/gap-analysis.md), [references/migration-plan.md](references/migration-plan.md). Live contracts: [references/policy-engine.md](references/policy-engine.md), [references/kb-layout.md](references/kb-layout.md), [references/evaluation-cases.md](references/evaluation-cases.md). Policy v1.0 content: **synthetic-policies** [SKILL.md](../synthetic-policies/SKILL.md).

Data model: **synthetic-data** [data-modeling.md](../synthetic-data/references/data-modeling.md), [schema.md](../synthetic-data/references/schema.md).

## Architectural principle

Three sources. **Do not mix them.**

| Question | Source | Path |
|----------|--------|------|
| What happened? | DB | `app/models/` + scoped tools |
| What does TechStore allow? | Rules | `app/policies/` + `data/company/company.yaml` |
| How do we explain it? | Documents | `data/knowledge_base/` → pgvector |

**Never** index orders, payments, shipments, or the product catalog in `kb_chunks`.

## Company context

| Concept | Value |
|---------|-------|
| Brand | **TechStore** — site, suporte, chat, KB, agent system prompts |
| Segment | Brazilian electronics e-commerce, web-only support |
| Catalog | Generic SKUs in `app/synthetic/catalogs.py` (no real trademarks) |
| Orders | Fulfillment status, payment rows, shipment row; labels from yaml |

Agents cite **generic product names** from `products.name` — never invent brands.

## Tool contract

v1 tools (PostgreSQL + policy engine, not in-memory dicts):

```
get_customer / verify_identity
get_order / get_order_items
get_payments / get_payment_status
get_shipment / get_shipping_status
get_return_status
check_refund_eligibility
create_refund_request
create_return_request
cancel_order
search_knowledge_base
```

The Assistant does **not** open Tickets. There is no `create_support_ticket` tool (ADR-0007). A Customer or Human Agent starts a Ticket in the UI; Escalation pauses the current Ticket.

**Order DTO** (from `order_to_dict`): `public_id`, `status`, `total_amount`, `currency`, `created_at`, `estimated_delivery`, `actual_delivery`, plus payment/shipment via their tools. Portuguese labels: `company.yaml` `labels.*`.

Rules:

- Portal scope: authenticated customer only.
- **One payment per order** in tools (except when surfacing duplicate-charge investigation).
- `cancel_order` denied when shipment has started — policy engine.
- `create_refund_request` must call the policy engine.

## Graph / agent behavior

State includes `orders_summary` (see `realtime-chat`) and `load_customer_context` before supervisor.

Workers use bound-tool loops. Supervisor intents: `billing | logistics | account | unknown`.

## Policies vs procedures vs FAQ

Invoke **synthetic-policies** to draft or sync TechStore policy v1.0 into yaml + KB + engine. KB under `data/knowledge_base/` — all references **TechStore**.

- Payment: **PIX + credit card** only (policy v1.0)
- Withdrawal: **7 days** CDC (`withdrawal.legal_days`) vs **30 days** commercial refund
- Shipping: carrier SLAs in yaml; **48h** damage report (operational)
- Warranty: legal 90d durable + category bands from yaml

## Evaluation and security

Cases tied to `SCN-*`. Utterances use generic product language. Negative security tests stay in `tests/`.

## What not to do

- Do not reference NexaCommerce, NexaPhone, or real brand names in new KB/tools.
- Do not dump operational tables or catalog into RAG.
- Do not restore in-memory `DEMO_*` dicts as source of truth.
- Do not add `create_support_ticket` to domain tools.
- Local data refresh: `generate_data.py --replace`.

## Done when

Invariants to preserve (already landed unless a change regresses them):

- [ ] Tools read PostgreSQL; no in-memory operational dicts
- [ ] KB says TechStore with testable rules matching yaml (`test_policy_docs_sync`)
- [ ] Graph loads customer context before the supervisor; evals use `SCN-*`
- [ ] Policy engine enforces window, threshold, and related gates
- [ ] `create_support_ticket` is absent from tool lists and `TOOL_PERMISSIONS`
