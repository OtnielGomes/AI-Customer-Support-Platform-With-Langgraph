# Simulation clock: frozen in CI, `--as-of today` for local demo

Order dates, delivery windows, and Policy `days_since_delivery` are offsets from one anchor. CI and evals use `simulation.clock: frozen` plus `simulation.now` in `company.yaml` so `SCN-*` stay deterministic. Local bootstrap passes `--as-of today` so the same offsets sit on the real calendar. Runtime Policy reads `SIMULATION_AS_OF` (typically `today`) so it does not keep measuring against a frozen August date after a wall-clock seed. Switching the committed yaml to `wall_clock` would make evals non-reproducible; omitting `--as-of today` on a local seed makes demo Orders look weeks old.

Status: accepted

Considered Options: always wall-clock (breaks CI); always frozen (unrealistic local demo); persist the anchor in the database (extra table for one timestamp).
