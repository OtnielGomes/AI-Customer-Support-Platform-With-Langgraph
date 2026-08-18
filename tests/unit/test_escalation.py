"""Unit tests for customer-facing escalation replies."""

from app.agents.escalation import run_escalation_agent


async def test_escalation_keeps_reason_off_customer_reply() -> None:
    """The interrupt reason must not be concatenated into draft_answer."""
    draft = (
        "Verifiquei e houve mesmo uma duplicação no pagamento do pedido ORD-01001. "
        "Posso encaminhar essa tratativa para você agora."
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
    assert "especialista humano" in result["draft_answer"]
