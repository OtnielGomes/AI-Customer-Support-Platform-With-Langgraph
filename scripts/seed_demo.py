"""Seed demo customer and operational TechStore data."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from app.persistence import get_session_factory
from app.synthetic import generate_world
from app.synthetic.graph import load_company_yaml
from app.synthetic.persist import export_scenarios, operational_row_count, persist_world

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _seed(as_of: str | None) -> None:
    """Generate the demo profile when the database is empty."""
    company = load_company_yaml()
    world = generate_world(profile="demo", seed=42, company=company, as_of=as_of)
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


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--as-of",
        default="today",
        help="Simulation clock: 'today' or an ISO-8601 instant. Default: today.",
    )
    args = parser.parse_args()

    async def _main() -> None:
        await _seed(args.as_of)

    if sys.platform == "win32":
        asyncio.run(_main(), loop_factory=asyncio.SelectorEventLoop)
    else:
        asyncio.run(_main())


if __name__ == "__main__":
    main()
