"""Support workflow graph assembly."""

import logging
from typing import Any

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, StateGraph
from psycopg_pool import AsyncConnectionPool

from app.config import get_settings
from app.graph.edges import resolution_node, route_after_supervisor, route_after_worker
from app.graph.nodes import (
    account_node,
    billing_node,
    escalation_node,
    input_guardrails_node,
    load_customer_context_node,
    logistics_node,
    output_guardrails_node,
    supervisor_node,
)
from app.graph.state import SupportState

logger = logging.getLogger(__name__)


async def build_support_graph(checkpointer: AsyncPostgresSaver | None = None) -> Any:
    """Build and compile the support StateGraph."""
    graph = StateGraph(SupportState)

    graph.add_node("input_guardrails", input_guardrails_node)
    graph.add_node("load_customer_context", load_customer_context_node)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("billing", billing_node)
    graph.add_node("logistics", logistics_node)
    graph.add_node("account", account_node)
    graph.add_node("escalation", escalation_node)
    graph.add_node("resolution", resolution_node)
    graph.add_node("output_guardrails", output_guardrails_node)

    graph.set_entry_point("input_guardrails")
    graph.add_edge("input_guardrails", "load_customer_context")
    graph.add_edge("load_customer_context", "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "billing": "billing",
            "logistics": "logistics",
            "account": "account",
            "escalation": "escalation",
        },
    )
    graph.add_conditional_edges(
        "billing",
        route_after_worker,
        {"resolution": "resolution", "escalation": "escalation"},
    )
    graph.add_conditional_edges(
        "logistics",
        route_after_worker,
        {"resolution": "resolution", "escalation": "escalation"},
    )
    graph.add_conditional_edges(
        "account",
        route_after_worker,
        {"resolution": "resolution", "escalation": "escalation"},
    )
    graph.add_edge("resolution", "output_guardrails")
    graph.add_edge("escalation", "output_guardrails")
    graph.add_edge("output_guardrails", END)

    return graph.compile(checkpointer=checkpointer)


async def create_checkpointer() -> tuple[AsyncPostgresSaver, AsyncConnectionPool]:
    """Create Postgres checkpointer and connection pool."""
    settings = get_settings()
    pool = AsyncConnectionPool(
        conninfo=settings.checkpoint_database_url(),
        max_size=10,
        open=False,
        kwargs={"autocommit": True},
    )
    await pool.open()
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()
    return checkpointer, pool
