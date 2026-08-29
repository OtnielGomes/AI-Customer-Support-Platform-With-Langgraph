"""Shared LLM tool-calling loop for domain workers."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool

from app.config import build_chat_model
from app.policies.engine import escalation_from_facts
from app.security.authentication import Principal
from app.security.authorization import AuthorizationError, authorize_tool
from app.tools.context import get_tool_context

logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 4
HISTORY_WINDOW = 12


def bind_ticket_customer(customer_id: str | None) -> None:
    """Scope tools to the ticket customer when context exists."""
    context = get_tool_context()
    if context is None or not customer_id:
        return
    try:
        context.customer_id = uuid.UUID(str(customer_id))
    except ValueError:
        logger.warning("Invalid customer_id on graph state: %s", customer_id)


def _tool_map(tools: list[BaseTool]) -> dict[str, BaseTool]:
    return {tool.name: tool for tool in tools}


def _facts_from_tool_results(tool_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Flatten tool payloads into Facts the Escalation catalog can read."""
    facts: dict[str, Any] = {}
    for item in tool_results:
        result = item.get("result")
        if not isinstance(result, dict) or result.get("error"):
            continue
        name = item.get("tool")
        if name == "verify_identity":
            facts["identity_checked"] = True
            facts["identity_verified"] = result.get("verified")
            if result.get("account_status"):
                facts["account_status"] = result.get("account_status")
        if name in {"get_shipment", "get_shipping_status"}:
            if result.get("status"):
                facts["shipment_status"] = result.get("status")
            if "customer_received" in result:
                facts["customer_received"] = result.get("customer_received")
        if name == "evaluate_escalation":
            if result.get("escalation_trigger"):
                facts["escalation_trigger"] = result.get("escalation_trigger")
            facts["customer_insists_after_refusal"] = bool(
                result.get("customer_insists_after_refusal")
            )
        if result.get("account_status") and "account_status" not in facts:
            facts["account_status"] = result.get("account_status")
    return facts


async def run_tool_loop(
    *,
    system_prompt: str,
    user_message: str = "",
    history: list[Any] | None = None,
    tools: list[BaseTool],
    principal_scopes: list[str],
    extra_context: str = "",
) -> dict[str, Any]:
    """Call the chat model with bound tools until it stops or hits the iteration cap.

    Args:
        system_prompt: Worker instructions.
        user_message: Latest customer utterance when ``history`` is omitted.
        history: Optional conversation window (human/ai messages).
        tools: Domain tools plus KB search.
        principal_scopes: API key scopes used for authorize_tool.
        extra_context: Optional retrieved policy text prepended to the user turn.

    Returns:
        Partial graph state: draft_answer, tool_results, needs_human, policy_decision,
        refund_tool_success, refund_executed.
    """
    principal = Principal(key_id="graph", scopes=principal_scopes)
    tool_results: list[dict[str, Any]] = []
    policy_decision: dict[str, Any] | None = None
    refund_tool_success = False
    refund_executed = False
    model = build_chat_model().bind_tools(tools)
    tools_by_name = _tool_map(tools)

    messages: list[Any] = [SystemMessage(content=system_prompt)]
    window = list(history or [])[-HISTORY_WINDOW:]
    if window:
        messages.extend(window)
        if extra_context:
            messages.insert(1, HumanMessage(content=extra_context))
    else:
        human = user_message
        if extra_context:
            human = f"{extra_context}\n\nCustomer: {user_message}"
        messages.append(HumanMessage(content=human))

    answer = ""
    for _ in range(MAX_TOOL_ITERATIONS):
        response = await _astream_complete(model, messages)
        messages.append(response)
        tool_calls = getattr(response, "tool_calls", None) or []
        if not tool_calls:
            answer = (
                response.content if isinstance(response.content, str) else str(response.content)
            )
            break
        for call in tool_calls:
            name = call.get("name") if isinstance(call, dict) else getattr(call, "name", "")
            args = call.get("args") if isinstance(call, dict) else getattr(call, "args", {})
            call_id = call.get("id") if isinstance(call, dict) else getattr(call, "id", "")
            result: Any
            try:
                authorize_tool(principal, name)
                tool = tools_by_name.get(name)
                if tool is None:
                    result = {"error": f"Unknown tool {name}"}
                else:
                    result = await tool.ainvoke(args or {})
            except AuthorizationError as exc:
                result = {"error": str(exc)}
            except Exception as exc:
                logger.exception("Tool %s failed", name)
                result = {"error": str(exc)}
            tool_results.append({"tool": name, "result": result})
            if name == "check_refund_eligibility" and isinstance(result, dict):
                policy_decision = result
            if name == "evaluate_escalation" and isinstance(result, dict):
                policy_decision = result
            if name == "create_refund_request" and isinstance(result, dict):
                eligibility = result.get("eligibility")
                if isinstance(eligibility, dict):
                    policy_decision = eligibility
                if result.get("status") in {"requested", "pending_approval"}:
                    refund_tool_success = True
                if result.get("refund_executed"):
                    refund_executed = True
                if result.get("requires_human"):
                    merged: dict[str, Any] = dict(policy_decision or {})
                    merged["requires_human"] = True
                    policy_decision = merged
            messages.append(
                ToolMessage(
                    content=json.dumps(result, default=str),
                    tool_call_id=call_id or name,
                )
            )
    else:
        last = messages[-1]
        answer = getattr(last, "content", "") if not isinstance(last, ToolMessage) else ""
        if not isinstance(answer, str):
            answer = str(answer)

    if not answer:
        answer = "I need more information to help with this request."

    needs_human = False
    if isinstance(policy_decision, dict) and policy_decision.get("requires_human"):
        needs_human = True
    catalog = escalation_from_facts(_facts_from_tool_results(tool_results))
    if catalog.escalate:
        needs_human = True
        merged_decision: dict[str, Any] = dict(policy_decision or {})
        merged_decision["requires_human"] = True
        if catalog.reasons:
            merged_decision["escalation_trigger"] = catalog.reasons[0].lower()
        policy_decision = merged_decision
    lowered = answer.lower()
    if "escalat" in lowered:
        needs_human = True

    return {
        "draft_answer": answer,
        "tool_results": tool_results,
        "needs_human": needs_human,
        "policy_decision": policy_decision,
        "refund_tool_success": refund_tool_success,
        "refund_executed": refund_executed,
        "messages": [AIMessage(content=answer)],
    }


async def _astream_complete(model: Any, messages: list[Any]) -> Any:
    """Stream a model turn so LangGraph can emit tokens, then return the full message."""
    stream = getattr(model, "astream", None)
    if stream is None:
        return await model.ainvoke(messages)
    assembled: Any = None
    async for chunk in stream(messages):
        assembled = chunk if assembled is None else assembled + chunk
    if assembled is None:
        return await model.ainvoke(messages)
    return assembled
