"""NexaCommerce synthetic data package."""

from __future__ import annotations

from typing import Any

from app.synthetic.anomalies import overlay_anomalies
from app.synthetic.graph import (
    PROFILES,
    assign_public_ids,
    assert_integrity,
    build_products,
    fill_happy_path,
    load_company_yaml,
    simulation_now,
)
from app.synthetic.records import World
from app.synthetic.rng import SeededRNG


def generate_world(
    profile: str = "demo",
    seed: int | None = None,
    company: dict[str, Any] | None = None,
) -> World:
    """Build a coherent in-memory company snapshot.

    Args:
        profile: ``demo``, ``v1``, or ``load``.
        seed: RNG seed; defaults to ``company.simulation.seed``.
        company: Loaded ``company.yaml`` mapping.

    Returns:
        Populated ``World`` with integrity already asserted.
    """
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile {profile!r}. Expected one of {sorted(PROFILES)}")
    cfg = company or load_company_yaml()
    rng = SeededRNG(seed if seed is not None else int(cfg["simulation"]["seed"]))
    now = simulation_now(cfg)
    volumes = PROFILES[profile]
    world = World(products=build_products(rng, volumes["products"]))
    overlay_anomalies(world, rng, now, cfg, volumes["anomaly_copies"])
    fill_happy_path(world, rng, now, cfg, volumes["customers"], volumes["orders"])
    if world.customers:
        world.customers[0].email = "demo@example.com"
        world.customers[0].name = "Demo Customer"
    assign_public_ids(world)
    assert_integrity(world)
    return world
