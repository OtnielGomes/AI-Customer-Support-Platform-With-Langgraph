# Phased migration (historical)

These phases **landed**. Do not re-run them. For new work, follow **company-architecture** (maintain three sources) and **synthetic-data** (extend the generator). Optional remaining deepening: shipping address columns, yaml catalog.

Ship in this order. Do not start phase 3 if phase 1 data is still dicts.

## Phase 0 — Skills and docs

Update `AGENTS.md` skill table (already done when these skills landed). When implementing, add `app/policies/` to the directory map and `ai-engineer-components` rule.

## Phase 1 — World + data

Follow **synthetic-data**:

1. `data/company/company.yaml`
2. Models + Alembic
3. `scripts/generate_data.py --profile demo --seed 42`
4. Wire `seed_demo` / bootstrap
5. Integrity tests

Exit criteria: `get_order` *could* be written against real rows (even if tools still dict).

## Phase 2 — Policy documents + ingest

1. Replace generic markdown with NexaCommerce tree ([kb-layout.md](kb-layout.md))
2. Numeric rules copied from yaml (30 days, R$1000, 10% restocking)
3. Warranty vs refund conflict documented
4. Extend `infer_domain()`; re-ingest
5. Quarantine injection fixture **out** of default ingest

## Phase 3 — Policy engine

1. `app/policies/` loads yaml
2. `can_refund` / `can_cancel` / `requires_identity` as pure functions
3. Unit tests from [policy-engine.md](policy-engine.md)
4. Tool `check_refund_eligibility` wraps the engine

Exit criteria: tests pass **without** an LLM.

## Phase 4 — Tools

1. Replace `DEMO_*` in billing, logistics, account
2. Session injection; customer scoping
3. `permissions.py` updated; authorization still runs **before** each tool
4. `create_refund_request` never returns `approved` unless engine says auto-execute (v1: prefer `requested` / `pending_approval`)
5. Rewrite `tests/unit/test_billing_tools.py` (current tests assert auto-approve — they must change)

## Phase 5 — Graph and agents

1. `ecosystem-primer` + `langgraph-docs`
2. Extend `SupportState`
3. Replace heuristic tool picks with a tool-calling worker
4. After tools: if policy `requires_human`, route to escalation (existing HITL)
5. `validate_output` still blocks refund claims without successful **eligible** tool path

## Phase 6 — Evaluation

1. Import `data/fixtures/scenarios.json` into `app/evaluation/datasets/`
2. Add policy-compliance and unauthorized-action metrics
3. First PR: ≥15 cases covering the 10 scenario groups in the architecture brief
4. Later: 50–100 cases; pytest in `tests/evaluation/`
5. Never write target percentages into README until a run produced them

## Phase 7 — Security pack

1. Negative utterances from synthetic-data anomalies.md
2. Guardrail + policy engine both refuse
3. Optional RAG injection eval (opt-in ingest)

## Suggested first PR slice

Phases 1–3 + `get_order` / `get_payments` / `check_refund_eligibility` only. Do not rewrite the whole UI.
