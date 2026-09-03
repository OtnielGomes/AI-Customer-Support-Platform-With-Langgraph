---
name: synthetic-data
description: "INVOKE FIRST when generating, seeding, or expanding TechStore synthetic operational data — product categories, 180-SKU generic catalog, customers, orders with payment/delivery/fulfillment status and fictional shipping address, payments, shipments, returns, refunds, support tickets, labeled anomalies, and evaluation fixtures. Use when the user asks to create fake/demo/company data, a synthetic data generator, seed PostgreSQL with coherent electronics e-commerce records, add double-charge or delayed-shipment scenarios, write scripts/generate_data.py, data/company/company.yaml, data/company/product_catalog.yaml, or fixtures for agent evals. Do not use for policy/KB markdown (synthetic-policies) or Docker/env bootstrap (project-setup)."
compatibility: "Python 3.12, uv, SQLAlchemy async, PostgreSQL. Windows scripts must use SelectorEventLoop. Read company-architecture before changing tools, policies, or the graph."
---

# TechStore synthetic data

Build a **coherent operational world**, not random rows. Agents must look up real state (`ORD-01042` exists, payment `confirmed`, order `in_transit`). Random IDs with no graph make evaluation impossible.

This skill covers **data + world model + anomaly catalog**. Wiring tools, policy engine, and RAG is **company-architecture**.

## Skill order

```
project-setup                  → DB up, Alembic, port 5433, Windows event loop
synthetic-data (this)          → schema fields, catalog, generator, fixtures
synthetic-policies             → policy v1.0 yaml + KB + engine constants
company-architecture           → tools, policy engine wiring, graph, evals
```

Read [references/data-modeling.md](references/data-modeling.md) **first** (requirements → SQL). Then [references/schema.md](references/schema.md), [references/catalog.md](references/catalog.md), [references/simulation-clock.md](references/simulation-clock.md), [references/anomalies.md](references/anomalies.md), [references/distributions.md](references/distributions.md).

## Confirmed decisions

| Topic | Decision |
|-------|----------|
| Brand | **TechStore** — site, suporte, chat, KB, `company.name` in yaml |
| Catalog | Generic names in `app/synthetic/catalogs.py` (no Intel, Sony, Logitech, etc.). Yaml 180-SKU file is optional deepening. |
| Prices | `price_bands` in yaml + **seeded RNG** per SKU (deterministic) |
| Shipping | Fictional **delivery address on `orders`** (rua, CEP, cidade, UF) |
| Payments | **One row per order**; two rows only for `SCN-DOUBLE-PAY-*` |
| Categories | **Top-level only** on products; subcategories optional for nav |
| Local DB | **`--replace`** — no backfill of legacy NexaCommerce seeds |
| Order dates | **`orders.created_at`** — anchor via `simulation.clock` (frozen) or `--as-of today` (local bootstrap) |

## Current repo (do not ignore)

| Exists today | Implication |
|--------------|-------------|
| `customers` with UUID PK, `public_id`, tier, account status | Keep UUID internally; tools/evals/chat use `public_id` |
| `tickets`, `ticket_messages`, `kb_chunks`, operational tables | Tickets **are** support cases. Facts live in PostgreSQL. |
| `scripts/seed_demo.py` | Calls generator `--profile demo` |
| `app/tools/*/tools.py` | DB-backed tools (`lookups.py`). Do not restore in-memory operational dicts. |
| Catalog | Generic names in `app/synthetic/catalogs.py` + `ProductCategory` StrEnum (6 categories in `company.yaml`). No NexaPhone / trademark names. |
| `data/company/company.yaml` | World constants, policy numbers, labels |

When **extending** (optional, not a migration): shipping address columns on `orders`, `product_categories` table, 180-SKU yaml. See [schema.md](references/schema.md) and [catalog.md](references/catalog.md).

## Three-source rule (data side)

| Source | Answers | Generator writes? |
|--------|---------|-------------------|
| PostgreSQL | What happened? | **Yes** — operational facts |
| `data/company/company.yaml` | Company constants, labels, price bands | **Yes** |
| `app/synthetic/catalogs.py` | SKU names (generic) | **Yes** (code catalog; yaml SKU file is optional) |
| `data/knowledge_base/` | How TechStore explains policies | **No** — **synthetic-policies** skill |

Never put order/payment/shipment **rows** into RAG.

## Target company: TechStore

Brazilian **electronics & technology** e-commerce. Web-only support. Locale `pt_BR`, currency `BRL`, timezone `America/Sao_Paulo`.

Copy [assets/company.yaml.example](assets/company.yaml.example) only when creating a **new** world file. Live constants: `data/company/company.yaml`. Catalog names: `app/synthetic/catalogs.py` (generic). A yaml SKU catalog is an optional extension — see [catalog.md](references/catalog.md).

**Orders** expose today:

| Field | Storage |
|-------|---------|
| Número do pedido | `orders.public_id` |
| Status de pagamento | `payments.status` → labels in yaml |
| Forma de pagamento | `payments.payment_method` |
| Data do pedido | `orders.created_at` |
| Total | `orders.total_amount` |
| Itens | `order_items` + `products` |
| Previsão / entrega real | `orders.estimated_delivery`, `orders.actual_delivery` |
| Status do pedido | `orders.status` |

`delivery_method` and `orders.shipping_*` are optional schema deepening — [schema.md](references/schema.md).

DB enums: English `snake_case`. Portuguese labels: `company.yaml` `labels.*`.

## Identity scheme

| Entity | `public_id` | PK |
|--------|-------------|-----|
| Category | `CAT-00001` | UUID |
| Customer | `CUST-00001` | UUID |
| Product | `PRD-00001` | UUID |
| Order | `ORD-01001` | UUID |
| Order item | `ITM-00001` | UUID |
| Payment | `PAY-00001` | UUID |
| Shipment | `SHP-00001` | UUID |
| Return | `RET-00001` | UUID |
| Refund | `RFD-00001` | UUID |

## Workflow

### 1. World model + catalog

`company.yaml` + `product_catalog.yaml`. Generator uses Faker `pt_BR` for `orders.shipping_*`.

### 2. Schema (Alembic)

Operational tables landed in `003_nexa_operational.py`; chat in `004_chat_messages.py`. Keep UUID PKs and `public_id`. Additive migrations only.

Optional deepening (only when the user asks): `product_categories` + `orders.shipping_*` / `delivery_method` — [schema.md](references/schema.md).

### 3. Generator

```
product_categories → products (generic SKUs, seeded prices)
customers → orders (+ shipping address) → order_items
→ payments (1 row) → shipments → returns → refunds → tickets → synthetic_scenarios
```

CLI: `--profile demo|v1 --seed 42 --replace [--as-of today]`.

Bootstrap (`scripts/bootstrap.ps1`) seeds with `--as-of today` so demo order dates are relative to the run date. CI and unit tests keep `simulation.clock: frozen` in yaml. See [references/simulation-clock.md](references/simulation-clock.md).

### 4. Integrity checks

- `sum(order_items.line_total) == order.total_amount`
- Exactly **one** payment per order unless `double_payment` scenario
- `shipping_postal_code` valid Brazilian CEP format
- `delivery_deadline` matches `delivery_method` SLA unless delayed anomaly

### 5–7. Anomalies, seed, tests

Unchanged pattern — see [references/anomalies.md](references/anomalies.md). After schema change, local bootstrap: `uv run python scripts/generate_data.py --profile demo --seed 42 --replace`.

## What not to do

- Do not use real brand/trademark names in catalog or agent fixtures.
- Do not use NexaCommerce / NexaPhone / NexaBook naming in new seeds.
- Do not put fixed per-SKU prices in yaml (use `price_bands` + seed).
- Do not add split PIX+card on one order.
- Do not backfill legacy enum rows — use `--replace`.

## Done when

Invariants to preserve when changing seed/generator:

- [ ] `company.yaml` is TechStore; catalog names stay generic (no trademarks)
- [ ] Generator `--profile demo --seed 42 --replace` is deterministic; anomaly kinds in [anomalies.md](references/anomalies.md)
- [ ] Tools keep reading PostgreSQL (`public_id`, payments, shipments)
- [ ] Unit tests cover catalog integrity, prices, and the single-payment rule

Optional catalog/shipping deepening is **not** required to close a seed-data task.
