# Intent taxonomy — policy v1.0 → tools

Supervisor v1 keeps `billing | logistics | account | unknown`. Use `policy_type` on tickets, eval cases, and future metadata — not new graph workers yet.

## Classification map

| `policy_type` | Policy § | Typical utterance (PT) | Primary worker | Tools (order) |
|---------------|----------|--------------------------|----------------|---------------|
| `ORDER` | 2 | "Cadê meu pedido?" | logistics | `get_order`, `get_order_items` |
| `PAYMENT` | 5, 16 | "PIX não confirmou" / cobrança duplicada | billing | `get_payments`, `check_refund_eligibility` |
| `CANCELLATION` | 6 | "Quero cancelar" | billing | `get_order`, `cancel_order` |
| `SHIPPING` | 7 | "Quando chega?" / Sedex | logistics | `get_order`, `get_shipment` |
| `DELIVERY` | 7–8 | "Não recebi" / atraso | logistics | `get_shipment`, `get_order` |
| `DAMAGED_PRODUCT` | 8 | "Caixa amassada" / avaria | logistics → billing | `get_order`, RAG damage procedure |
| `WRONG_PRODUCT` | 9 | "Veio produto errado" | logistics | `get_order_items`, RAG wrong_item |
| `WITHDRAWAL` | 10 | "Arrependimento" / 7 dias CDC | billing | `check_refund_eligibility` (withdrawal reason) |
| `RETURN` | 11 | "Quero devolver" | billing | `check_refund_eligibility`, `create_return_request` |
| `REFUND` | 16 | "Quero reembolso" | billing | `check_refund_eligibility`, `create_refund_request` |
| `WARRANTY` | 12–13 | "Produto com defeito" | billing | warranty RAG + `check_refund_eligibility` (defect) |
| `TECHNICAL_SUPPORT` | 14 | "Assistência técnica" | account / billing | RAG + escalate |
| `FRAUD` | 15 | chargeback suspeito | billing | escalate, identity |
| `CUSTOMER_ACCOUNT` | 2.2, 15 | conta / senha | account | `get_customer`, `verify_identity` |
| `PRIVACY` | 22 | dados pessoais | account | RAG privacy summary, escalate |

## Decision flow (return request)

```text
User: "Quero devolver meu produto"
        ↓
Intent: RETURN_REQUEST (policy_type RETURN or WITHDRAWAL)
        ↓
Tools: get_customer → get_order → get_order_items → get_payments
        ↓
Engine inputs:
  - days_since_delivery
  - withdrawal.legal_days (7) vs refund.standard_window_days (30)
  - reason: customer_preference | withdrawal | defective_product
  - final_sale, amount, identity_verified
        ↓
check_refund_eligibility / can_refund / can_cancel
        ↓
Eligible → create_return_request or create_refund_request
Ineligible → explain (RAG + policy_ids)
requires_human → escalate
```

## SCN-* fixture mapping

| Scenario | `policy_type` | Engine note |
|----------|---------------|-------------|
| `SCN-DOUBLE-PAY-*` | `PAYMENT` | `duplicate_charge=True` |
| `SCN-DELAYED-SHIP-*` | `DELIVERY` | no auto-refund |
| `SCN-DELIVERED-MISSING-*` | `DELIVERY` | not preference return |
| `SCN-REFUND-OUTSIDE-WINDOW-*` | `REFUND` | `OUTSIDE_WINDOW` |
| `SCN-DEFECT-WARRANTY-*` | `WARRANTY` | defect path + warranty RAG |
| `SCN-HIGH-VALUE-REFUND-*` | `REFUND` | `requires_human` |
| `SCN-CANCEL-AFTER-SHIP-*` | `CANCELLATION` | `SHIPPED_USE_RETURN` |
| `SCN-FINAL-SALE-*` | `RETURN` | `FINAL_SALE` |

## RAG metadata (future)

When splitting KB files, optional frontmatter:

```yaml
policy_type: RETURN
topic: commercial_return_window
effective_date: "2026-08-01"
applicability: post_delivery
priority: 10
```

Ingest may map `policy_type` → `KBChunk.domain` or a custom metadata field if the retriever supports filters.
