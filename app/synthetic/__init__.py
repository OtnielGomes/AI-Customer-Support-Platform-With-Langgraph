"""NexaCommerce synthetic data package."""

from __future__ import annotations

from typing import Any

from app.synthetic.anomalies import overlay_anomalies
from app.synthetic.demo_customer import build_demo_showcase
from app.synthetic.graph import (
    DEMO_LOGIN_EMAIL,
    DEMO_LOGIN_NAME,
    DEMO_SHOWCASE_EMAIL,
    PROFILES,
    allocate_login_email,
    assert_integrity,
    assign_public_ids,
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
    build_demo_showcase(world, rng, now, cfg)
    fill_happy_path(world, rng, now, cfg, volumes["customers"], volumes["orders"])
    _apply_demo_login(world)
    assign_public_ids(world)
    assert_integrity(world)
    return world


def _apply_demo_login(world: World) -> None:
    """Pin the first customer to a documented portal login email."""
    if not world.customers:
        return
    for customer in world.customers[1:]:
        if customer.email.lower() == DEMO_LOGIN_EMAIL:
            customer.email = allocate_login_email(world, customer.name, 99)
    if world.customers[0].email.lower() != DEMO_SHOWCASE_EMAIL:
        world.customers[0].email = DEMO_LOGIN_EMAIL
        world.customers[0].name = DEMO_LOGIN_NAME
