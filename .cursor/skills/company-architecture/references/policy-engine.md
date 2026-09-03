# Deterministic policy engine

The LLM extracts intent and arguments. **Python** decides critical eligibility.

```
LLM → intent/args → policy engine → tool persist → LLM wording
```

## Module layout

```
app/policies/
  __init__.py
  loader.py      # read data/company/company.yaml (cached)
  types.py       # RefundDecision, CancelDecision (Pydantic)
  engine.py      # orchestrate
  rules.py       # pure functions
```

Do not import LangChain here. Do not call the chat model.

## RefundDecision (minimum fields)

```python
eligible: bool
requires_human: bool
reasons: list[str]          # stable codes: OUTSIDE_WINDOW, FINAL_SALE, ...
restocking_fee_rate: Decimal | None
max_amount: Decimal | None
policy_ids: list[str]       # e.g. refund_policy, warranty_policy
```

## `can_refund` inputs

- `days_since_delivery` from **delivery** date when delivered; if not delivered, preference refund usually ineligible — use cancellation rules
- `order_total` / requested `amount` (`Decimal`)
- `product_category`, `final_sale`
- `reason`: `customer_preference` | `defective_product` | `withdrawal` (CDC — `withdrawal.legal_days`) | duplicate paths
- `customer_tier` (only if yaml defines a perk; default: **no** gold extra window)
- `identity_verified: bool`
- `warranty_days` + `days_since_delivery`

## Rules to encode (must match yaml + markdown)

1. **Withdrawal** within `withdrawal.legal_days` (7) after delivery → eligible (`withdrawal_policy`)
2. Preference refund within `standard_window_days` (30) after delivery → eligible
3. Preference outside window → deny (`OUTSIDE_WINDOW`) unless warranty/defect path applies
4. `final_sale` + preference → deny (`FINAL_SALE`)
5. Amount > `approval_threshold_brl` → `requires_human=True` even if eligible
6. Defective → no restocking fee; preference → `restocking_fee_rate`
7. Identity not verified → deny or `requires_human` (`IDENTITY_REQUIRED`) — do not execute
8. Refunds return via original payment method (engine outputs a flag; tool enforces)
9. Duplicate paid payments: eligible for **one** duplicate amount; reason code `DUPLICATE_CHARGE`; skip return window if the charge is verified duplicate (still require identity)
10. Electronics inspection: if category in electronics and days_since_delivery > `electronics_inspection_after_days` and reason involves physical return → `inspection_required` (may still be eligible)

## Cancellation

- Allowed while shipment not yet `shipped` / `in_transit` / `delivered`
- After ship: deny cancel; suggest return procedure (`SHIPPED_USE_RETURN`)

## Tests (`tests/unit/test_policy_engine.py`)

Table-driven cases, no LLM:

| Case | Expect |
|------|--------|
| Delivered 10d, preference, R$200 | eligible, no human |
| Delivered 35d, preference | deny OUTSIDE_WINDOW |
| Delivered 35d, defective, within warranty | eligible path via warranty codes (or requires_human) — **not** silent deny |
| R$3500 otherwise eligible | requires_human |
| final_sale preference | deny |
| identity_verified=False | not executed |
| duplicate charge R$899 | eligible duplicate, no restocking |
| shipped order cancel | deny cancel |

## Consistency test

`tests/unit/test_policy_docs_sync.py`: read yaml; assert `30`, `1000`, `0.10` (or the yaml values) appear in `data/knowledge_base/policies/refund_policy.md`. Fails if docs drift.
