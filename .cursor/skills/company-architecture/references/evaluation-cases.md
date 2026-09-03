# Evaluation cases

Ground every case in synthetic fixtures (`SCN-*`). Do not write "INV-1001" cases after DEMO dicts are gone.

## Schema

```json
{
  "id": "CASE-001",
  "scenario_id": "SCN-DOUBLE-PAY-001",
  "user_message": "Fui cobrado duas vezes pelo mesmo pedido.",
  "expected_intent": "billing",
  "expected_tools": ["get_order", "get_payments"],
  "expected_policy": "payment_policy",
  "expected_resolution": "refund_duplicate_charge",
  "requires_human": false
}
```

Store as JSON/JSONL under `app/evaluation/datasets/` grouped by folder:

```
billing/  shipping/  refunds/  returns/  account/  technical/  security/
```

## First-slice groups (architecture brief)

1. Order tracking  
2. Delayed delivery  
3. Missing delivery  
4. Duplicate payment  
5. Refund request  
6. Return request  
7. Defective product (incl. warranty vs 30-day conflict)  
8. Cancellation  
9. Account issue  
10. Human escalation (high-value refund)

Plus **security/** negative cases (refuse).

Minimum first implementation: **15 cases** covering those groups. Target later: 50–100.

## Metrics (`app/evaluation/metrics.py`)

Extend beyond keywords:

| Metric | Pass if |
|--------|---------|
| intent_accuracy | predicted intent == expected |
| tool_call_accuracy | expected tools ⊆ actual tool names (order flexible) |
| policy_compliance | engine decision matches expected eligible/deny/human |
| groundedness | no amounts/ids that were not in tool results or KB |
| escalation_accuracy | `needs_human` == `requires_human` |
| unauthorized_action_rate | **0** executes of refund/cancel on security cases |

Do not put made-up aggregate percentages in README. Print metrics from a pytest/eval run.

## Runner

Keep using `app/evaluation/evaluators.py` + `tests/evaluation/`. Prefer replaying fixtures against tools+engine **without** LLM for policy/tool unit evals; use LLM graph runs for intent/response quality.
