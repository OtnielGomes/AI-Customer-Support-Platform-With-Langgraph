"""Seed demo customer and operational TechStore data."""

from __future__ import annotations

import asyncio
import logging
import sys

from app.synthetic.graph import load_company_yaml
from app.synthetic.persist import export_scenarios, operational_row_count, persist_world
from app.synthetic import generate_world
from app.persistence import get_session_factory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Generate the demo profile when the database is empty."""
    company = load_company_yaml()
    world = generate_world(profile="demo", seed=42, company=company)
    factory = get_session_factory()
    async with factory() as session:
        existing = await operational_row_count(session)
        if existing:
            logger.info("Operational data already present (%s customers); skipping seed", existing)
            return
        await persist_world(session, world)
        await session.commit()
    export_scenarios(world)
    logger.info("Seed complete: %s customers, %s orders", len(world.customers), len(world.orders))


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop)
    else:
        asyncio.run(main())
