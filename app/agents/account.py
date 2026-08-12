"""Account domain agent."""

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.config import build_chat_model
from app.security.authentication import Principal
from app.security.authorization import AuthorizationError, authorize_tool
from app.tools.account.tools import ACCOUNT_TOOLS

logger = logging.getLogger(__name__)

ACCOUNT_SYSTEM = """You are an account support agent.
Help with profile info, password resets, and account settings.
Use tools when appropriate. Escalate sensitive issues to humans."""


async def run_account_agent(
    user_message: str,
    principal_scopes: list[str],
) -> dict[str, Any]:
    """Run account domain agent."""
    principal = Principal(key_id="graph", scopes=principal_scopes)
    tool_results: list[dict[str, Any]] = []
    lowered = user_message.lower()

    if "password" in lowered or "reset" in lowered:
        for tool in ACCOUNT_TOOLS:
            if tool.name == "reset_account_password":
                try:
                    authorize_tool(principal, tool.name)
                    result = tool.invoke({"customer_id": "default"})
                    tool_results.append({"tool": tool.name, "result": result})
                except AuthorizationError as exc:
                    tool_results.append({"tool": tool.name, "error": str(exc)})
    else:
        for tool in ACCOUNT_TOOLS:
            if tool.name == "get_account_profile":
                try:
                    authorize_tool(principal, tool.name)
                    result = tool.invoke({"customer_id": "default"})
                    tool_results.append({"tool": tool.name, "result": result})
                except AuthorizationError as exc:
                    tool_results.append({"tool": tool.name, "error": str(exc)})

    model = build_chat_model()
    response = await model.ainvoke(
        [
            SystemMessage(content=ACCOUNT_SYSTEM),
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
