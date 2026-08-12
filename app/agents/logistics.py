"""Logistics domain agent."""

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.config import build_chat_model
from app.security.authentication import Principal
from app.security.authorization import AuthorizationError, authorize_tool
from app.tools.logistics.tools import LOGISTICS_TOOLS

logger = logging.getLogger(__name__)

LOGISTICS_SYSTEM = """You are a logistics support agent.
Help customers with shipping status, delivery tracking, and address updates.
Use tools when order IDs are mentioned. Escalate if you cannot help."""


async def run_logistics_agent(
    user_message: str,
    principal_scopes: list[str],
) -> dict[str, Any]:
    """Run logistics domain agent."""
    principal = Principal(key_id="graph", scopes=principal_scopes)
    tool_results: list[dict[str, Any]] = []
    order_id = _extract_order_id(user_message)

    if order_id:
        for tool in LOGISTICS_TOOLS:
            if tool.name == "get_shipment_status":
                try:
                    authorize_tool(principal, tool.name)
                    result = tool.invoke({"order_id": order_id})
                    tool_results.append({"tool": tool.name, "result": result})
                except AuthorizationError as exc:
                    tool_results.append({"tool": tool.name, "error": str(exc)})

    model = build_chat_model()
    response = await model.ainvoke(
        [
            SystemMessage(content=LOGISTICS_SYSTEM),
            HumanMessage(
                content=f"Tool results:\n{json.dumps(tool_results)}\nCustomer: {user_message}"
            ),
        ]
    )
    answer = response.content if isinstance(response.content, str) else str(response.content)
    return {
        "draft_answer": answer,
        "tool_results": tool_results,
        "needs_human": "escalat" in answer.lower(),
        "messages": [AIMessage(content=answer)],
    }


def _extract_order_id(text: str) -> str | None:
    """Extract order ID from message."""
    import re

    match = re.search(r"ORD-\d+", text.upper())
    return match.group(0) if match else None
