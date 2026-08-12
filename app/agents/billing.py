"""Billing domain agent."""

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.config import build_chat_model
from app.security.authentication import Principal
from app.security.authorization import AuthorizationError, authorize_tool
from app.tools.billing.tools import BILLING_TOOLS
from app.tools.knowledge_base.tools import search_knowledge_base

logger = logging.getLogger(__name__)

BILLING_SYSTEM = """You are a billing support agent.
Use available tools to investigate invoices and charges.
Search the knowledge base for billing policies before answering.
If you cannot resolve the issue, say you need to escalate to a human.
Be concise and accurate. Do not promise refunds unless request_refund succeeded."""


async def run_billing_agent(
    user_message: str,
    principal_scopes: list[str],
    kb_context: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run billing agent with tool authorization checks."""
    principal = Principal(key_id="graph", scopes=principal_scopes)
    tool_results: list[dict[str, Any]] = []
    refund_tool_success = False

    # Try KB search first if context not provided
    kb_chunks = kb_context or []
    if not kb_chunks:
        try:
            authorize_tool(principal, "search_knowledge_base")
            kb_result = await search_knowledge_base.ainvoke(
                {"query": user_message, "domain": "billing"}
            )
            if isinstance(kb_result, list):
                kb_chunks = kb_result
                tool_results.append({"tool": "search_knowledge_base", "result": kb_result})
        except AuthorizationError as exc:
            logger.warning("KB search unauthorized: %s", exc)
        except Exception as exc:
            logger.warning("KB search failed: %s", exc)

    # Heuristic tool selection for demo vertical slice
    lowered = user_message.lower()
    if "invoice" in lowered or "inv-" in lowered:
        for tool in BILLING_TOOLS:
            if tool.name == "get_invoice":
                try:
                    authorize_tool(principal, tool.name)
                    invoice_id = _extract_invoice_id(user_message)
                    if invoice_id:
                        result = tool.invoke({"invoice_id": invoice_id})
                        tool_results.append({"tool": tool.name, "result": result})
                except AuthorizationError as exc:
                    tool_results.append({"tool": tool.name, "error": str(exc)})

    if "charge" in lowered or "invoice" in lowered or "bill" in lowered:
        for tool in BILLING_TOOLS:
            if tool.name == "list_charges":
                try:
                    authorize_tool(principal, tool.name)
                    result = tool.invoke({"customer_id": "default"})
                    tool_results.append({"tool": tool.name, "result": result})
                except AuthorizationError as exc:
                    tool_results.append({"tool": tool.name, "error": str(exc)})

    if "refund" in lowered or "reembolso" in lowered:
        for tool in BILLING_TOOLS:
            if tool.name == "request_refund":
                try:
                    authorize_tool(principal, tool.name)
                    invoice_id = _extract_invoice_id(user_message) or "INV-1001"
                    result = tool.invoke({"invoice_id": invoice_id, "reason": user_message})
                    tool_results.append({"tool": tool.name, "result": result})
                    if isinstance(result, dict) and result.get("status") == "approved":
                        refund_tool_success = True
                except AuthorizationError as exc:
                    tool_results.append({"tool": tool.name, "error": str(exc)})

    context_block = ""
    if kb_chunks:
        context_block = "Knowledge base:\n" + json.dumps(kb_chunks, indent=2)
    tools_block = ""
    if tool_results:
        tools_block = "Tool results:\n" + json.dumps(tool_results, indent=2)

    model = build_chat_model()
    response = await model.ainvoke(
        [
            SystemMessage(content=BILLING_SYSTEM),
            HumanMessage(content=f"{context_block}\n{tools_block}\nCustomer: {user_message}"),
        ]
    )

    answer = response.content if isinstance(response.content, str) else str(response.content)
    needs_human = "escalat" in answer.lower() or "human" in answer.lower()

    return {
        "draft_answer": answer,
        "tool_results": tool_results,
        "retrieved_context": kb_chunks,
        "needs_human": needs_human,
        "refund_tool_success": refund_tool_success,
        "messages": [AIMessage(content=answer)],
    }


def _extract_invoice_id(text: str) -> str | None:
    """Extract invoice ID pattern from text."""
    import re

    match = re.search(r"INV-\d+", text.upper())
    return match.group(0) if match else None
