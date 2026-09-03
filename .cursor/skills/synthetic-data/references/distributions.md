# Volumes and distributions

`simulation_now` / `resolve_simulation_now` in `company.yaml` sets the anchor for relative dates. Default **`clock: frozen`** + `simulation.now` for evals; **`--as-of today`** on CLI overrides for local demo.

## Profiles

| | demo | v1 | load (optional) |
|--|------|----|-----------------|
| customers | 20 | 1_000 | 10_000 |
| products | 180 (full catalog) | 180 (full catalog) | 180 (reuse catalog) |
| orders | 40 | 3_000 | 25_000 |
| order_items | ~70 | ~3_500 | ~35_000 |
| payments | ~50 | ~3_500 | ~30_000 |
| shipments | ~35 | 3_000 | 25_000 |
| returns | 8 | 300 | 5_000 |
| refunds | 6 | 200 | 3_000 |
| tickets | 15 | 400 | 2_000 |
| labeled scenarios | all kinds, ≥1 each | all kinds, ≥3 each | same as v1 plus volume |

Allow ±10% on v1/load counts. `demo` must still include **every** anomaly kind.

## Customer mix (v1)

| Tier | Share | Notes |
|------|-------|-------|
| standard | 55% | |
| silver | 25% | |
| gold | 15% | more orders, slightly more refunds |
| enterprise | 5% | higher AOV; more human-approval refunds |

Account status: 92% `active`, 6% `suspended`, 2% `closed`. Closed/suspended customers still have historical orders.

Orders per customer: Pareto-ish — many 1–2 orders, some 8–15 (gold/enterprise). **Invariant:** every customer has ≥ 1 order (assign leftover happy-path orders only after each customer has one).

## Login emails

Portal identity is email. Generator emails must look like real logins, stay unique, and stay deterministic for `--seed 42`:

- Domains rotate: `gmail.com`, `outlook.com`, `uol.com.br`, `nexamail.com`
- Local part: `{first}.{last}` plus a numeric suffix when needed (`ana.costa@gmail.com`, `pedro.lima2@outlook.com`)
- Anomaly customers use the same scheme (not `delayed.1@example.com`)
- Scenario fixtures stay keyed by `customer_public_id` / `order_public_id`, not by email
- Canonical demo customer (first row after generate) keeps a documented login used in README / AGENTS.md

## Order / payment / shipment

Order status mix (after overlays):

| Status | Share (approx) |
|--------|----------------|
| delivered | 55% |
| shipped / in_transit / out_for_delivery | 20% |
| processing / paid | 10% |
| pending | 3% |
| cancelled | 7% |
| returned | 5% |

AOV: mix of accessories (R$49–299), mid (R$300–1_499), laptops/phones (R$1_500–8_999) so both sides of the R$1_000 approval threshold exist.

Payments: 80% single `paid`; remainder failed-then-paid, pending, or labeled anomalies.

Carriers (weight from yaml): Correios, Jadlog, DHL, FedEx.

Shipping time: 3–12 days from `created_at`. Delayed anomaly: `estimated_delivery` < `simulation_now` and status still `in_transit` or `delayed`.

## Returns / refunds

Returns only from delivered (or shipped+delivered) orders unless a labeled scenario says otherwise.

Reason mix: 40% customer_preference, 30% defective_product, 15% wrong_item, 10% missing_parts, 5% other.

Electronics returned after 7 days: set `inspection_status=pending` more often (policy hook).

Refunds: duplicate-charge refunds have `return_id=null`. Preference refunds may be `requested` not `executed`. Amounts > threshold: `pending_approval` + `requires_human_approval=true`.

## Determinism

- `Faker('pt-BR')` + `random.Random(seed)` (or numpy Generator). Reset Faker seed too.
- Same `--seed` + `--profile` ⇒ same public_ids and scenario ids.
- Do not call `uuid.uuid4()` without a seeded UUID generator (`uuid.UUID(int=rng.getrandbits(128), version=4)`).
