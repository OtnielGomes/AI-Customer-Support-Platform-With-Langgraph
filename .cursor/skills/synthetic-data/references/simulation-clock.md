# Simulation clock (order dates)

Order `created_at`, delivery dates, and anomaly windows are **offsets** from a single anchor: `resolve_simulation_now()`.

## Precedence (highest first)

| Priority | Source | Use case |
|----------|--------|----------|
| 1 | CLI `--as-of today` | Local bootstrap, fresh demo relative to real today |
| 2 | CLI `--as-of 2026-08-14T12:00:00-03:00` | Pin a specific instant without editing yaml |
| 3 | `simulation.clock: wall_clock` in yaml | Always use real now (rare; prefer `--as-of`) |
| 4 | `simulation.clock: frozen` + `simulation.now` | **Default** — CI, evals, deterministic `SCN-*` |

## yaml

```yaml
simulation:
  clock: frozen          # frozen | wall_clock
  now: "2026-08-14T12:00:00-03:00"
  seed: 42
```

Timezone: `company.timezone` (`America/Sao_Paulo`).

## CLI

```powershell
# Deterministic (frozen yaml) — CI and regression
uv run python scripts/generate_data.py --profile demo --seed 42 --replace

# Anchor at real today — local demo
uv run python scripts/generate_data.py --profile demo --seed 42 --replace --as-of today

# Pin explicit instant
uv run python scripts/generate_data.py --profile demo --seed 42 --replace --as-of 2026-08-14T12:00:00-03:00
```

`scripts/bootstrap.ps1` runs `seed_demo.py --as-of today` on empty DB.

## Order date field

| Field | Meaning |
|-------|---------|
| `orders.created_at` | Data da compra / data do pedido |
| Offsets | `created_at = anchor - timedelta(days=N)` per scenario |

Same `seed` + same anchor → same `public_id` and same day offsets. Changing anchor shifts all order dates together; anomaly **shapes** (outside window, delayed ETA) stay valid.

Happy-path (non-`SCN-*`) Orders are created within the last **15 days**, with age coherent with status (`pending`/`paid` recent, `shipped` still inside ETA, `delivered` older). Labeled scenarios keep their own offsets.

Runtime Policy (`days_since_delivery`) uses `SIMULATION_AS_OF` (local `.env` typically `today`) so it matches an `--as-of today` seed. CI leaves the env unset and keeps the frozen yaml clock for generator tests.

## Tests

- Default tests use **frozen** yaml (no `--as-of`).
- Add tests for `--as-of today` with mocked `datetime.now` when testing wall clock.

## Do not

- Use `wall_clock` in committed `company.yaml` for CI — breaks deterministic evals.
- Expect `seed_demo` to refresh dates if DB already has rows (it skips when data exists; use `generate_data.py --replace --as-of today`).
