---
name: synthetic-policies
description: "INVOKE when drafting, splitting, syncing, or updating TechStore commercial policies — orders, payments (PIX/cartão), shipping, delivery, cancellation, arrependimento (CDC 7 days), returns, refunds, warranty, fraud, and KB RAG documents. Use when the user asks to write or align policy markdown, extend data/company/company.yaml with policy constants, map policy sections to app/policies/rules.py, intent taxonomy (ORDER/PAYMENT/RETURN), ingest_kb domains, or replace NexaCommerce policy text. Read synthetic-data for yaml layout and company-architecture for the three-source split. Do not use for seed rows alone (synthetic-data), chat/SSE (realtime-chat), or Docker bootstrap (project-setup)."
compatibility: "TechStore policy v1.0. Requires data/company/company.yaml, data/knowledge_base/, app/policies/. Aligns with synthetic-data, company-architecture, realtime-chat."
---

# TechStore synthetic policies (v1.0)

Turn the **TechStore Política Comercial v1.0** into three coordinated layers agents can use without contradiction:

| Layer | Answers | Path |
|-------|---------|------|
| **Constants** | Numbers, enums, SLAs | `data/company/company.yaml` |
| **Engine** | May the tool run? | `app/policies/rules.py`, `engine.py` |
| **Documents** | How do we explain it? | `data/knowledge_base/` → pgvector |

Canonical prose: [assets/techstore_commercial_policy_v1.md](assets/techstore_commercial_policy_v1.md).

## Skill order

```
project-setup          → ingest_kb, bootstrap
synthetic-data         → company.yaml base (refund, warranty, shipping SLAs)
synthetic-policies (this) → policy v1.0 → yaml + KB split + engine mapping
company-architecture   → tools, graph, evals (consumes synced policies)
realtime-chat          → agent explains outcomes; never invents policy numbers
```

Read [references/yaml-constants.md](references/yaml-constants.md) before editing yaml. Read [references/kb-split.md](references/kb-split.md) before writing markdown. Read [references/intent-taxonomy.md](references/intent-taxonomy.md) before eval cases or supervisor metadata. Read [references/engine-vs-rag.md](references/engine-vs-rag.md) before changing `app/policies/`.

## Operating model (policy facts)

| Fact | Value |
|------|-------|
| Brand | **TechStore** |
| Channels | 100% online — no physical store, no pickup, no marketplace |
| Payments | **PIX** and **cartão de crédito** only (v1.0 policy) |
| Delivery | Address on order; Sedex (3 bd) / standard (7 bd) per `company.yaml` |
| Arrependimento CDC | **7 days** from receipt (legal) — separate from commercial refund window |
| Commercial refund window | **30 days** after delivery (preference) — engine + yaml |
| Transport damage report | **48 hours** after receipt (operational, not a legal waiver) |
| High-value refund approval | **R$ 1.000** — human required |

## Workflow

### 1. Extend `company.yaml`

Add or align keys from [references/yaml-constants.md](references/yaml-constants.md) and [assets/company-policy-extensions.yaml.example](assets/company-policy-extensions.yaml.example). **Numbers live in yaml first** — never only in markdown.

### 2. Split policy into KB files

Follow [references/kb-split.md](references/kb-split.md). Policies = testable numbered rules in **English** (eval stability). FAQ = Portuguese customer-facing "how". Procedures = steps **after** engine says eligible.

Run after edits:

```powershell
uv run python scripts/ingest_kb.py
```

### 3. Encode enforceable rules in the engine

Only rules the **tool must enforce** go in `app/policies/rules.py` — see [references/engine-vs-rag.md](references/engine-vs-rag.md). Prose-only sections (responsibilities, privacy principles) stay in KB.

### 4. Intent taxonomy for agents and evals

Map customer utterances → `policy_type` → tools — [references/intent-taxonomy.md](references/intent-taxonomy.md). Supervisor stays `billing | logistics | account`; fine labels live on tickets/evals.

### 5. Sync test

```powershell
uv run pytest tests/unit/test_policy_engine.py tests/unit/test_policy_docs_sync.py -q
```

`test_policy_docs_sync.py` must fail if yaml numbers drift from `data/knowledge_base/policies/*.md`.

### 6. Agent behavior (realtime-chat)

- Explain using **tool/engine result** + RAG snippet — not memory.
- Cite **TechStore**; no NexaCommerce.
- Arrependimento (7d) vs devolução comercial (30d): use correct term per case.
- Do not promise off-channel PIX or password collection (policy §15).

## Three-source rule (do not mix)

| Content | Goes in |
|---------|---------|
| Order status, payment row, tracking | PostgreSQL only |
| `withdrawal.legal_days: 7`, `refund.standard_window_days: 30` | yaml + engine + policy markdown |
| "Como solicitar devolução" steps | procedures + FAQ (RAG) |
| Operational order `ORD-01042` | never in kb_chunks |

## Alignment with synthetic-data

- Generator payment methods should match yaml `payment.methods` (`pix`, `credit_card`).
- `final_sale` SKUs support policy §4 / refund deny rules.
- Anomalies (`SCN-*`) must be explainable under policy v1.0 (duplicate charge, delay, delivered-missing, etc.).

## What not to do

- Do not paste the full 24-section policy into a single RAG chunk — split per [kb-split.md](references/kb-split.md).
- Do not let the LLM decide refund/cancel eligibility without `check_refund_eligibility` / engine.
- Do not add boleto/debit if policy v1.0 is authoritative (unless yaml explicitly extends methods).
- Do not index `assets/techstore_commercial_policy_v1.md` as one blob — derive focused KB files.
- Do not contradict CDC: 7-day arrependimento is **legal**; 30-day window is **commercial preference** path.

## Done when

- [ ] `company.yaml` includes policy v1.0 constants (withdrawal, damage_report, payment methods)
- [ ] KB policies/procedures/faq/company reference **TechStore** with testable rules matching yaml
- [ ] `app/policies/rules.py` enforces yaml numbers; arrependimento path documented
- [ ] `intent-taxonomy.md` linked to tools and `SCN-*` fixtures
- [ ] `ingest_kb.py` + `test_policy_docs_sync.py` pass
- [ ] `company-architecture` and `realtime-chat` skills point here for policy work
