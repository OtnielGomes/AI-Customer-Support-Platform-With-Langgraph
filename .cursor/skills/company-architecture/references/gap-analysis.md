# Gap analysis — historical

The FAQ-chatbot → three-source migration **landed**. Use this file to avoid regressing working infrastructure, not as a to-do list. Remaining deepening (shipping address on orders, yaml SKU catalog) is optional extension — see **synthetic-data**.

## Keep as-is

| Piece | Path | Why |
|-------|------|-----|
| FastAPI entry, tickets API, SSE | `app/api/` | Portal/console already depend on it |
| Supervisor + 3 workers + escalation | `app/agents/`, `app/graph/` | Right pattern; deepen, don't replace with a single mega-agent |
| pgvector RAG pipeline | `app/retrieval/`, `kb_chunks` | Correct for **documents** |
| Auth, scopes, guardrails | `app/security/` | Extend tool names and checks |
| Langfuse / OTel | `app/observability/` | Attach `ticket_id` + `order_public_id` when present |
| Next.js in `web/` | BFF injects API key | No architecture change required for v1 data model besides displaying public ids later |
| Alembic `001`/`002`, UUID PKs | `migrations/` | Additive migrations only |
| Redis cache | `app/cache/` | Still not source of truth |

## Replace / extend

| Current | Problem | Target |
|---------|---------|--------|
| `Customer` = email+name | No tier/status/phone | Extend columns + `public_id` |
| Flat `ProductCategory` enum (6 SKUs) | Not a real electronics catalog | `product_categories` + 180-SKU yaml |
| Orders without shipping address | Logistics tools cannot cite CEP/cidade | `orders.shipping_*` columns |
| v1 order/payment enums (`paid`, `shipped`) | Does not match PT fulfillment flow | v2 enums + `delivery_method`; `--replace` locally |
| `DEMO_INVOICES`, `DEMO_SHIPMENTS`, `DEMO_ACCOUNTS` | Not enterprise state | Scoped DB tools |
| `request_refund` → `status=approved` | LLM+tool bypass policy | `create_refund_request` + engine |
| `run_billing_agent` keyword ifs | Not tool-calling | Bound tools + policy tool |
| KB generic FAQs / NexaCommerce naming | Untestable, wrong brand | TechStore policies/procedures/faq/company |
| `seed_demo` 1 ticket | Cannot eval | Generator profiles |
| `BILLING_DATASET` 5 keyword cases | No grounding in DB | `SCN-*` cases |
| `evaluate_keywords` | Weak | policy compliance + tool-call accuracy |
| `infer_domain` only 3 folders | Breaks new KB tree | Map path prefixes |
| `SupportState` thin | No company context | Customer/order/policy fields |

## Explicit non-goals (v1)

- MCP servers (`Customer MCP`, `Order MCP`, …)
- Subscriptions table
- Renaming `tickets` → `support_tickets`
- String primary keys
- 10k-row default seed
- New worker per fine-grained intent
- Putting Next.js in `app/`
- Measuring and publishing fake 87% accuracy in README
