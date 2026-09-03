# Knowledge base layout

Canonical split for TechStore policy v1.0: **synthetic-policies** [kb-split.md](../synthetic-policies/references/kb-split.md). This file is the legacy overview; prefer kb-split when adding policy files.

```
data/knowledge_base/
├── company/
│   ├── company_overview.md
│   └── support_guidelines.md
├── policies/
│   ├── refund_policy.md
│   ├── return_policy.md
│   ├── shipping_policy.md
│   ├── warranty_policy.md
│   ├── payment_policy.md
│   └── account_policy.md
├── procedures/
│   ├── refund_procedure.md
│   ├── escalation_procedure.md
│   └── identity_verification.md
└── faq/
    ├── shipping_faq.md
    ├── payments_faq.md
    └── returns_faq.md
```

## Writing rules

- TechStore, Brazil, BRL, Portuguese **or** English consistently per file; prefer **English for policies** (eval/tool stability) and Portuguese FAQ if the portal is PT — do not mix conflicting numbers across languages.
- Every numeric rule appears in `company.yaml` first.
- Policies are **testable** (lists of numbered rules), not marketing.
- Procedures describe steps **after** eligibility (verify identity → create return → inspect → refund tool).
- FAQs explain customer-facing "how", not live order status.

## Domain mapping for ingest

Update `infer_domain()`:

| Path contains | `KBChunk.domain` |
|---------------|------------------|
| `/policies/refund` `/policies/payment` `/faq/payments` | `billing` |
| `/policies/shipping` `/policies/return` `/faq/shipping` `/faq/returns` | `logistics` |
| `/policies/account` `/procedures/identity` | `account` |
| `/company/` `/procedures/escalation` | `general` |

Workers still pass `domain=` to `search_knowledge_base`. For warranty vs refund conflicts, the billing worker should search **billing and** a warranty query (or `domain=general` plus refund). Do not rely on a single top-k=3 billing search to load warranty.

## Indirect injection

Place any malicious "ignore previous instructions" fixture under `data/knowledge_base/_eval_injection/` and **exclude** that directory in `ingest_kb.py` unless `INCLUDE_INJECTION_CORPUS=1`. Default bootstrap must stay clean.
