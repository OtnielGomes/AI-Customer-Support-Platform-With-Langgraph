"""Simulation clock for generator dates and Policy day counts."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo


def company_timezone(company: dict[str, Any]) -> ZoneInfo:
    """Return the merchant timezone from the world model."""
    name = str(company.get("company", {}).get("timezone") or "America/Sao_Paulo")
    return ZoneInfo(name)


def resolve_simulation_now(
    company: dict[str, Any],
    *,
    as_of: str | datetime | None = None,
) -> datetime:
    """Resolve the simulation anchor.

    Precedence: ``as_of`` (``today`` or ISO-8601), then ``simulation.clock``
    ``wall_clock``, then frozen ``simulation.now``.
    """
    tz = company_timezone(company)
    if as_of is not None:
        return _parse_as_of(as_of, tz)
    clock = str(company.get("simulation", {}).get("clock") or "frozen").strip().lower()
    if clock == "wall_clock":
        return datetime.now(tz)
    return datetime.fromisoformat(str(company["simulation"]["now"]))


def _parse_as_of(as_of: str | datetime, tz: ZoneInfo) -> datetime:
    """Parse a CLI/env anchor into a timezone-aware instant."""
    if isinstance(as_of, datetime):
        if as_of.tzinfo is None:
            return as_of.replace(tzinfo=tz)
        return as_of
    text = str(as_of).strip()
    if not text or text.lower() == "today":
        return datetime.now(tz)
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=tz)
    return parsed
