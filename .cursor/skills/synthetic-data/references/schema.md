# TechStore operational schema (v2)

Read [data-modeling.md](data-modeling.md) for requirements → SQL workflow. Read [catalog.md](catalog.md) for the 180-SKU list.

## Invariants

- PostgreSQL only. UUID primary keys (`as_uuid=True`).
- Human/agent identifiers are unique `public_id` string columns (`CUST-00001`, `PRD-00180`).
- Timezone-aware `DateTime(timezone=True)`.
- `StrEnum` columns: `Enum(..., name="...", values_callable=lambda x: [e.value for e in x])`.
- Keep existing `tickets`, `resolutions`, `agent_runs`, `kb_chunks` tables.
- Extend `customers`; do not drop email uniqueness.
- **DB values:** English `snake_case`. **Customer-facing labels:** Portuguese via `company.yaml` `labels.*`.

## Enums

```text
CustomerTier:        standard | silver | gold | enterprise
AccountStatus:       active | suspended | closed

OrderStatus (fulfillment):
  picking | picked | posted | in_transit | out_for_delivery | delivered | cancelled | returned

PaymentStatus:
  pending_confirmation | confirmed | declined | refunded | partially_refunded

PaymentMethod:       credit_card | debit_card | pix | boleto

DeliveryMethod:      express_sedex | standard

ShipmentStatus:      processing | shipped | in_transit | out_for_delivery | delivered | delayed | lost

ReturnStatus:        requested | pending_inspection | approved | rejected | completed | cancelled
ReturnReason:        defective_product | wrong_item | customer_preference | missing_parts | other
InspectionStatus:    pending | passed | failed | not_required
RefundStatus:        requested | pending_approval | approved | executed | denied
```

### Label mapping (company.yaml — not DB columns)

| DB value | Portuguese label (agent/UI) |
|----------|----------------------------|
| `pending_confirmation` | Em processo de confirmação de pagamento |
| `confirmed` | Pagamento confirmado |
| `declined` | Pagamento recusado |
| `picking` | Em separação |
| `picked` | Pedido separado |
| `posted` | Pedido postado |
| `in_transit` | Pedido em rota de entrega |
| `out_for_delivery` | Pedido saiu para o destinatário |
| `delivered` | Pedido entregue |
| `express_sedex` | Rápida Sedex (até 3 dias úteis) |
| `standard` | Entrega padrão (até 7 dias úteis) |

Migration note: v1 used `OrderStatus.pending|paid|processing|shipped` and `PaymentStatus.paid|pending`. **Local dev:** run `generate_data.py --replace` after migration — do not backfill legacy NexaCommerce/NexaPhone rows.

## Tables

### product_categories (new — replaces flat ProductCategory enum)

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| public_id | String unique | `CAT-00001` |
| slug | String | unique with `parent_id` |
| name_pt | String | |
| parent_id | UUID FK nullable | self-reference |
| sort_order | Integer | |

Seed **18 top-level** categories. Optional nav subcategories — products FK **top-level only**.

### customers (extend)

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | existing |
| public_id | String unique | `CUST-00001` |
| name | String | existing |
| email | String unique | existing |
| phone | String nullable | E.164 |
| customer_tier | Enum | default `standard` |
| account_status | Enum | default `active` |
| created_at | DateTime TZ | existing |

### products

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| public_id | String unique | `PRD-00001` — registration number |
| sku | String unique | `TS-HW-01` |
| name | String | generic catalog name (no trademarks) |
| category_id | UUID FK product_categories | top-level category only |
| unit_price | Numeric(12,2) | BRL — from seeded `price_bands` |
| final_sale | Boolean | default false |
| warranty_days | Integer | from category band |
| active | Boolean | |

### orders

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| public_id | String unique | `ORD-01001` — order number |
| customer_id | UUID FK customers | indexed |
| status | Enum | fulfillment — see OrderStatus |
| total_amount | Numeric(12,2) | |
| currency | String(3) | `BRL` |
| created_at | DateTime TZ | order date |
| delivery_method | Enum | `express_sedex` \| `standard` |
| delivery_deadline | DateTime TZ | contractual deadline |
| estimated_delivery | DateTime TZ nullable | forecast |
| actual_delivery | DateTime TZ nullable | when delivered |
| shipping_street | String | fictional delivery address |
| shipping_number | String nullable | |
| shipping_complement | String nullable | |
| shipping_neighborhood | String | bairro |
| shipping_city | String | |
| shipping_state | String(2) | UF |
| shipping_postal_code | String | CEP `00000-000` |

Payment method is on `payments.payment_method`. **One payment row per order** except `SCN-DOUBLE-PAY-*`. Aggregate payment status for tools/DTOs: that single row's status, or `declined`.

### order_items

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| public_id | String unique | `ITM-00001` |
| order_id | UUID FK orders | |
| product_id | UUID FK products | |
| quantity | Integer | ≥ 1 |
| unit_price | Numeric(12,2) | snapshot at purchase |
| line_total | Numeric(12,2) | quantity * unit_price |

### payments

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| public_id | String unique | `PAY-00001` |
| order_id | UUID FK orders | indexed |
| status | Enum | PaymentStatus |
| amount | Numeric(12,2) | |
| payment_method | Enum | |
| transaction_id | String unique | synthetic PSP id |
| created_at | DateTime TZ | |

Normal orders: one `confirmed` row. `double_payment`: two `confirmed` rows, same amount — **only labeled scenario**.

### shipments

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| public_id | String unique | `SHP-00001` |
| order_id | UUID FK orders | unique for v1 |
| carrier | String | from company.yaml |
| tracking_code | String unique | |
| status | Enum | ShipmentStatus |
| shipped_at | DateTime TZ nullable | aligns with `orders.status=posted` |
| estimated_delivery | DateTime TZ nullable | may match `orders.estimated_delivery` |
| delivered_at | DateTime TZ nullable | |
| customer_received | Boolean nullable | `false` = delivered-but-missing anomaly |

### returns, refunds, tickets, synthetic_scenarios

Same as v1 — see previous sections. Update anomaly shapes to use new `OrderStatus` / `PaymentStatus` names (`confirmed` not `paid`, `posted`/`in_transit` not `shipped` where precise).

## Fulfillment timeline (generator)

For a happy-path `standard` order:

```
created_at
  → payment pending_confirmation (0–2h)
  → payment confirmed → order picking (same day)
  → picked (+4–12h) → posted (+1d) → in_transit (+1–2d)
  → out_for_delivery (+delivery_method window) → delivered
```

`express_sedex`: `delivery_deadline` = created_at + 3 business days; `standard` = +7 business days. `estimated_delivery` ≤ `delivery_deadline` unless `SCN-DELAYED-SHIP-*`.

## Indexes (minimum)

- Unique on every `public_id`
- `product_categories.slug` + `parent_id`
- `products.category_id`, `products.sku`
- `orders.customer_id`, `orders.status`, `orders.created_at`
- `payments.order_id`, `payments.status`
- `shipments.tracking_code`, `shipments.status`
- `returns.order_id`, `refunds.order_id`
- `orders.shipping_postal_code`, `orders.shipping_city`
- `tickets.order_id`

## Numeric type

Use `Numeric(12, 2)` / `Decimal` in Python. Do not use float for money.
