# Engine vs RAG — what goes where

| Rule | Engine (`app/policies/`) | RAG only |
|------|--------------------------|----------|
| Refund within 30 days (preference) | `can_refund` | explain in `refund_policy.md` |
| Arrependimento 7 days CDC | `can_refund` with `reason=withdrawal` | `withdrawal_policy.md` |
| Refund > R$ 1000 needs human | `requires_human=True` | `refund_policy.md` |
| `final_sale` deny preference | `FINAL_SALE` code | `refund_policy.md` |
| Restocking 10% | `restocking_fee_rate` output | `refund_policy.md` |
| Identity required | `IDENTITY_REQUIRED` | `account_policy.md` + procedure |
| Duplicate charge refund | `duplicate_charge=True` | `payment_policy.md` |
| Cancel before ship | `can_cancel` | `cancellation_policy.md` |
| Cancel after posted | deny `SHIPPED_USE_RETURN` | `cancellation_policy.md` |
| Defect + warranty window | warranty days in engine | `warranty_policy.md` |
| 48h damage report | **not** auto-deny in engine v1 — logistics procedure + human | `delivery_damage_policy.md` |
| Off-channel PIX forbidden | guardrail / refuse tool | `payment_policy.md`, `fraud_policy.md` |
| Force majeure delay | no auto-refund | `shipping_policy.md` |
| Customer responsibilities (§20) | — | `company/support_guidelines.md` |
| Privacy principles (§22) | — | `privacy_policy_summary.md` |
| Product compatibility advice | — | `product_policy.md`, FAQ |

## Engine extensions for policy v1.0

When implementing, add to `rules.py`:

1. **`reason=withdrawal`** — eligible within `withdrawal.legal_days` (7) from delivery; distinct from `customer_preference` + 30-day window.
2. **`payment_method`** — restitution path: PIX vs credit_card messaging in tools, not LLM.
3. **`can_cancel`** — align with order status `picking|picked` only (before `posted`).

## Policy IDs

Engine `policy_ids` should match KB filenames for traceability:

```python
policy_ids = ["withdrawal_policy", "refund_policy"]
```

## Tests

Extend `tests/unit/test_policy_engine.py`:

| Case | Expect |
|------|--------|
| Day 5 after delivery, `reason=withdrawal` | eligible (7d window) |
| Day 5, `reason=customer_preference` | eligible (within 30d) |
| Day 10, `reason=withdrawal` | deny (outside 7d CDC path) |
| Day 35, `reason=customer_preference` | deny `OUTSIDE_WINDOW` |
| Unpaid PIX timeout | cancel eligible (generator/tool, not refund) |

Keep `test_policy_docs_sync.py` in sync with yaml.
