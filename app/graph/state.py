"""LangGraph support workflow state."""

from typing import Annotated, Any, NotRequired

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class SupportState(TypedDict):
    """State schema for the customer support graph."""

    ticket_id: str
    customer_id: NotRequired[str]
    messages: Annotated[list[Any], add_messages]
    intent: NotRequired[str]
    confidence: NotRequired[float]
    retrieved_context: NotRequired[list[dict[str, Any]]]
    tool_results: NotRequired[list[dict[str, Any]]]
    needs_human: NotRequired[bool]
    draft_answer: NotRequired[str]
    refund_tool_success: NotRequired[bool]
    principal_scopes: NotRequired[list[str]]
