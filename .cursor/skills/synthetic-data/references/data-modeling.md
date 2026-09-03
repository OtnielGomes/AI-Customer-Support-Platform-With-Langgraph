# Data modeling workflow (TechStore)

Follow this order when extending schema, generator, or migrations. Do **not** skip straight to SQL.

## 1. Requirements

| Requirement | Decision |
|-------------|----------|
| Company | **TechStore** — Brazilian B2C electronics e-commerce, web-only support (single brand for site, chat, and policies) |
| Locale | `pt_BR`, currency `BRL`, timezone `America/Sao_Paulo` |
| Catalog | **180 fixed SKUs** (18 categories × 10 products), **generic names** — see [catalog.md](catalog.md) |
| Pricing | **Price bands per category** + seeded RNG (no fixed price table) |
| Order facts | Number, payment status, payment method, order date, total, delivery method, **shipping address**, items, delivery deadline, forecast, fulfillment status |
| Payments | **One payment per order** except labeled `double_payment` anomaly |
| Identity | UUID PK internally; `public_id` for agents, tools, and chat (`ORD-01042`, `PRD-00123`) |
| Local reset | `generate_data.py --replace` — no migration of legacy NexaCommerce rows |

## 2. Entities

```
product_categories (top-level + optional nav subcategories)
products
customers (extend)
orders (+ shipping address columns)
order_items
payments
shipments
returns → refunds
tickets (extend)
synthetic_scenarios
```

## 3. Attributes (high level)

### product_categories

| Attribute | Notes |
|-----------|-------|
| `public_id` | `CAT-00001` |
| `slug` | English snake_case (`hardware`, `peripherals`) |
| `name_pt` | Customer-facing label (`Hardware`, `Periféricos`) |
| `parent_id` | Nullable — top-level when null; subcategories optional for nav only |
| `sort_order` | Navigation order |

### products

| Attribute | Notes |
|-----------|-------|
| `public_id` | Registration number — `PRD-00001` |
| `sku` | Internal code, e.g. `TS-HW-01` |
| `name` | **Generic** name from catalog (no real brands) |
| `category_id` | FK → **top-level** `product_categories` only |
| `unit_price` | `Numeric(12,2)` BRL — from seeded `price_bands` |
| `final_sale` | Boolean — policy tests |
| `warranty_days` | By category band in `company.yaml` |
| `active` | Boolean |

### orders

| Attribute | Notes |
|-----------|-------|
| `public_id` | Order number — `ORD-01001` |
| `customer_id` | FK |
| `status` | Fulfillment lifecycle — see schema.md |
| `total_amount` | Sum of line items |
| `currency` | `BRL` |
| `created_at` | Order date |
| `delivery_method` | `express_sedex` \| `standard` |
| `delivery_deadline` | Contractual deadline (business days from `created_at`) |
| `estimated_delivery` | Carrier forecast (may move on delay scenarios) |
| `actual_delivery` | Set when `status=delivered` |
| `shipping_street` | Logradouro — fictional, Faker `pt_BR` |
| `shipping_number` | Nullable |
| `shipping_complement` | Nullable |
| `shipping_neighborhood` | Bairro |
| `shipping_city` | Cidade |
| `shipping_state` | UF, 2 chars (`SP`, `RJ`, …) |
| `shipping_postal_code` | CEP `00000-000` |

Payment method and payment status live on **`payments`**. Normal orders: **exactly one** payment row. Tools expose aggregate `payment_status` on order DTOs.

### order_items, payments, shipments, returns, refunds

Unchanged responsibilities from [schema.md](schema.md). Logistics tools (`get_shipment`, `get_order`) return shipping address from `orders.*` columns.

## 4. Relationships & cardinality

```
product_categories 1 — * product_categories (parent/child, nav only)
product_categories 1 — * products          (top-level FK only)
customers          1 — * orders
orders             1 — * order_items
products           1 — * order_items
orders             1 — 1 payments          (2 rows only for SCN-DOUBLE-PAY-*)
orders             0..1 — 1 shipments
orders             0..* returns
returns            0..* refunds
customers          1 — * tickets
orders             0..1 tickets
```

## 5. Keys

| Entity | PK | Business key |
|--------|-----|--------------|
| All operational tables | UUID | `public_id` unique, zero-padded |
| product_categories | UUID | `slug` unique per parent |
| payments | UUID | `transaction_id` unique (PSP) |
| shipments | UUID | `tracking_code` unique |

## 6. Normalization

- **3NF** for operational tables — price snapshot on `order_items` only.
- Shipping address on **`orders`** (delivery destination per order; may differ from customer profile later).
- Category tree optional for navigation; products do not require subcategory FK.

## 7. Logical model

```
Customer places order (with fictional shipping address)
  → one payment (pending_confirmation → confirmed | declined)
  → on confirmed: order picking → … → delivered
  → shipment row tracks carrier + tracking
```

Labels (Portuguese) from `company.yaml` `labels.*`. DB stores English `snake_case`.

## 8. Physical model & SQL

- Alembic migration after `003_nexa_operational.py`.
- Local dev: **`--replace`** truncates operational synthetic data and regenerates — no enum backfill of old NexaCommerce seeds.
- Extend `orders`: `delivery_method`, `delivery_deadline`, shipping address columns.
- Replace flat `ProductCategory` enum with `product_categories` + FK on `products`.

## 9. Generator sources

| Asset | Path |
|-------|------|
| World constants | `data/company/company.yaml` |
| SKU names | `data/company/product_catalog.yaml` (from [catalog.md](catalog.md)) |
| Code loader | `app/synthetic/catalogs.py` |

## Confirmed decisions (do not re-ask)

| Topic | Decision |
|-------|----------|
| Brand | **TechStore** only — site, suporte, KB, agent prompts |
| Prices | `price_bands` + seeded RNG per SKU |
| Shipping address | On `orders`, fictional (Faker `pt_BR`) |
| Payments | One per order; duplicate only in `double_payment` scenarios |
| Subcategory | Not required on products — top-level category only |
| Product names | Generic — no real trademarks |
| Existing DB | Regenerate with `--replace` locally |
