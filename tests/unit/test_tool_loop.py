"""Unit tests for the shared tool-calling loop."""

from unittest.mock import patch

from langchain_core.messages import AIMessage
from langchain_core.tools import StructuredTool

from app.agents.tool_loop import run_tool_loop


class _FakeModel:
    """Chat model double that emits one tool call then a final answer."""

    def __init__(self) -> None:
        self.calls = 0

    def bind_tools(self, tools):
        return self

    async def ainvoke(self, messages):
        self.calls += 1
        if self.calls == 1:
            return AIMessage(
                content="",
                tool_calls=[
                    {"name": "get_order", "args": {"order_id": "ORD-01001"}, "id": "call-1"}
                ],
            )
        return AIMessage(content="Order is delivered.")


async def test_tool_loop_authorizes_and_records_results() -> None:
    """The loop should authorize get_order and store the tool payload."""
    fake = _FakeModel()

    async def _get_order(order_id: str) -> dict:
        return {"public_id": order_id, "status": "delivered"}

    tool = StructuredTool.from_function(
        coroutine=_get_order,
        name="get_order",
        description="Get an order",
    )
    with (
        patch("app.agents.tool_loop.build_chat_model", return_value=fake),
        patch("app.agents.tool_loop.authorize_tool") as authorize,
    ):
        result = await run_tool_loop(
            system_prompt="test",
            user_message="Where is ORD-01001?",
            tools=[tool],
            principal_scopes=["read", "write"],
        )
    authorize.assert_called()
    assert result["draft_answer"] == "Order is delivered."
    assert result["tool_results"][0]["tool"] == "get_order"
    assert fake.calls == 2
