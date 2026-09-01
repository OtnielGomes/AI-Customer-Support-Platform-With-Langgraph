"""Unit tests for the shared tool-calling loop."""

from unittest.mock import patch

from langchain_core.messages import AIMessage
from langchain_core.tools import StructuredTool

from app.agents.tool_loop import run_tool_loop


class _FakeModel:
    """Chat model double that emits one tool call then a final answer."""

    def __init__(self) -> None:
        self.calls = 0

    def bind_tools(self, tools: list) -> "_FakeModel":
        return self

    async def ainvoke(self, messages: list) -> AIMessage:
        self.calls += 1
        if self.calls == 1:
            return AIMessage(
                content="",
                tool_calls=[
                    {"name": "get_order", "args": {"order_id": "ORD-01001"}, "id": "call-1"}
                ],
            )
        return AIMessage(content="Order is delivered.")


class _AnswerModel:
    """Chat model double that returns a final answer with no tool calls."""

    def __init__(self, content: str) -> None:
        self.content = content

    def bind_tools(self, tools: list) -> "_AnswerModel":
        return self

    async def ainvoke(self, messages: list) -> AIMessage:
        return AIMessage(content=self.content)


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


async def test_tool_loop_does_not_pause_on_escalat_wording() -> None:
    """A worker mention of 'escalat' is not a catalog Escalation."""
    fake = _AnswerModel("I will not escalate this; here are the items on ORD-01001.")
    with patch("app.agents.tool_loop.build_chat_model", return_value=fake):
        result = await run_tool_loop(
            system_prompt="test",
            user_message="What are the items?",
            tools=[],
            principal_scopes=["read"],
        )
    assert result["needs_human"] is False
    assert result["draft_answer"] == fake.content


async def test_tool_loop_does_not_pause_on_forwarding_wording() -> None:
    """Talking about forwarding without a catalog trigger keeps the Ticket Open."""
    fake = _AnswerModel("I am not forwarding you; ORD-01001 is delivered.")
    with patch("app.agents.tool_loop.build_chat_model", return_value=fake):
        result = await run_tool_loop(
            system_prompt="test",
            user_message="Help with my order",
            tools=[],
            principal_scopes=["read"],
        )
    assert result["needs_human"] is False


async def test_tool_loop_pauses_when_engine_requires_human() -> None:
    """A real catalog/engine gate still sets a human pause."""

    class _RequiresHumanModel:
        """Chat model double that calls check_refund_eligibility then answers."""

        def __init__(self) -> None:
            self.calls = 0

        def bind_tools(self, tools: list) -> "_RequiresHumanModel":
            return self

        async def ainvoke(self, messages: list) -> AIMessage:
            self.calls += 1
            if self.calls == 1:
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "check_refund_eligibility",
                            "args": {"order_id": "ORD-01001"},
                            "id": "call-1",
                        }
                    ],
                )
            return AIMessage(content="A Human Agent must review this Refund.")

    async def _check_refund(order_id: str) -> dict:
        return {"eligible": False, "requires_human": True, "order_id": order_id}

    tool = StructuredTool.from_function(
        coroutine=_check_refund,
        name="check_refund_eligibility",
        description="Check refund eligibility",
    )
    fake = _RequiresHumanModel()
    with (
        patch("app.agents.tool_loop.build_chat_model", return_value=fake),
        patch("app.agents.tool_loop.authorize_tool"),
    ):
        result = await run_tool_loop(
            system_prompt="test",
            user_message="Refund ORD-01001",
            tools=[tool],
            principal_scopes=["read", "write"],
        )
    assert result["needs_human"] is True
