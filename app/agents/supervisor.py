"""Supervisor agent for intent classification."""

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.config import build_chat_model, get_settings


class IntentClassification(BaseModel):
    """Structured output from supervisor."""

    intent: str = Field(description="billing, logistics, account, or unknown")
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(default="")


SUPERVISOR_SYSTEM = """You classify customer support ticket intent.
Return intent as one of: billing, logistics, account, unknown.
Billing: invoices, payments, refunds, charges.
Logistics: shipping, delivery, tracking, addresses.
Account: login, password, profile, subscription plan.
Use unknown when unclear or multi-domain."""


async def classify_intent(user_message: str) -> IntentClassification:
    """Classify ticket intent using structured LLM output."""
    model = build_chat_model().with_structured_output(IntentClassification)
    result = await model.ainvoke(
        [
            SystemMessage(content=SUPERVISOR_SYSTEM),
            HumanMessage(content=user_message),
        ]
    )
    if isinstance(result, IntentClassification):
        return result
    return IntentClassification(intent="unknown", confidence=0.0, rationale="parse_error")


def should_route_to_worker(intent: str, confidence: float) -> bool:
    """Determine if intent is confident enough for domain worker."""
    settings = get_settings()
    known_intents = {"billing", "logistics", "account"}
    return intent in known_intents and confidence >= settings.supervisor_confidence_threshold
