"""Evaluation cases grounded in synthetic NexaCommerce fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FIXTURES = Path("data/fixtures/scenarios.json")


def load_nexa_cases() -> list[dict[str, Any]]:
    """Load scenario fixtures as evaluation cases."""
    if not FIXTURES.exists():
        return []
    raw = json.loads(FIXTURES.read_text(encoding="utf-8"))
    cases = []
    for item in raw:
        cases.append(
            {
                "id": item["id"],
                "scenario_id": item["id"],
                "kind": item.get("kind"),
                "message": item.get("user_message") or item.get("user_message_pt") or "",
                "expected_intent": item.get("expected_intent"),
                "expected_tools": item.get("expected_tools") or [],
                "expected_policy": item.get("expected_policy"),
                "expected_resolution": item.get("expected_resolution"),
                "requires_human": bool(item.get("requires_human")),
                "should_escalate": bool(item.get("requires_human")),
                "customer_public_id": item.get("customer_public_id"),
                "order_public_id": item.get("order_public_id"),
            }
        )
    return cases


NEXA_DATASET = load_nexa_cases()
ALL_DATASETS = {"nexa": NEXA_DATASET, "billing": NEXA_DATASET}
