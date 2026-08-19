"""Unit tests for customer-facing escalation replies."""

from app.agents.escalation import (
    CUSTOMER_ESCALATION_MESSAGE,
    customer_escalation_reply,
    run_escalation_agent,
)


async def test_escalation_keeps_reason_off_customer_reply() -> None:
    """The interrupt reason must not be concatenated into draft_answer."""
    draft = (
        "Verifiquei e houve mesmo uma duplicação no pagamento do pedido ORD-01001. "
        "Posso encaminhar essa tratativa para um especialista agora."
    )
    result = await run_escalation_agent(reason=draft, draft_answer=draft)
    assert result["draft_answer"] == draft
    assert "Escalation reason" not in result["draft_answer"]
    assert result["escalation_reason"] == draft
    assert result["needs_human"] is True


async def test_escalation_uses_fallback_when_no_draft() -> None:
    """A missing worker reply still yields a customer-safe handoff message."""
    result = await run_escalation_agent(reason="Policy requires human review")
    assert "Escalation reason" not in result["draft_answer"]
    assert result["escalation_reason"] == "Policy requires human review"
    assert result["draft_answer"] == CUSTOMER_ESCALATION_MESSAGE
    assert "especialista" in result["draft_answer"]


async def test_escalation_appends_notice_when_worker_omits_handoff() -> None:
    """A worker explanation without a handoff still tells the customer."""
    draft = "Este reembolso de alto valor precisa de aprovação humana."
    reply = customer_escalation_reply(draft)
    assert draft in reply
    assert CUSTOMER_ESCALATION_MESSAGE in reply
    result = await run_escalation_agent(reason="high value", draft_answer=draft)
    assert result["draft_answer"] == reply
    assert "Escalation reason" not in result["draft_answer"]
