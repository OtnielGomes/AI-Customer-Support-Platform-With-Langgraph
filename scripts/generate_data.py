"""Generate coherent TechStore operational data."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from app.persistence import get_session_factory
from app.synthetic import generate_world
from app.synthetic.graph import load_company_yaml
from app.synthetic.persist import (
    export_scenarios,
    operational_row_count,
    persist_world,
    replace_operational_data,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _run(profile: str, seed: int, replace: bool) -> None:
    """Generate, optionally replace, persist, and export fixtures."""
    company = load_company_yaml()
    world = generate_world(profile=profile, seed=seed, company=company)
    factory = get_session_factory()
    async with factory() as session:
        existing = await operational_row_count(session)
        if existing and not replace:
            raise SystemExit(
                "Operational data already exists. Re-run with --replace to regenerate."
            )
        if existing and replace:
            await replace_operational_data(session)
        await persist_world(session, world)
        await session.commit()
    export_scenarios(world)
    logger.info(
        "Generated profile=%s seed=%s customers=%s orders=%s scenarios=%s",
        profile,
        seed,
        len(world.customers),
        len(world.orders),
        len(world.scenarios),
    )


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=["demo", "v1", "load"], default="demo")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()

    async def _main() -> None:
        await _run(args.profile, args.seed, args.replace)

    if sys.platform == "win32":
        asyncio.run(_main(), loop_factory=asyncio.SelectorEventLoop)
    else:
        asyncio.run(_main())


if __name__ == "__main__":
    main()
