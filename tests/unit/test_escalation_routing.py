"""Graph routing honors the closed Escalation catalog."""

from app.graph.edges import route_after_worker


def test_route_after_worker_escalates_on_fraud_trigger() -> None:
    """Fraud is Escalation, not resolution."""
    assert (
        route_after_worker({"policy_decision": {"escalation_trigger": "fraud"}})
        == "escalation"
    )


def test_route_after_worker_resolves_order_tracking() -> None:
    """Shipment lookup stays autonomous."""
    assert (
        route_after_worker({"policy_decision": {"escalation_trigger": "order_tracking"}})
        == "resolution"
    )


def test_route_after_worker_explains_lawful_refusal() -> None:
    """A coded refusal is not Escalation until the Customer insists."""
    state = {
        "policy_decision": {
            "escalation_trigger": "lawful_refusal",
            "customer_insists_after_refusal": False,
        }
    }
    assert route_after_worker(state) == "resolution"


def test_route_after_worker_escalates_when_customer_insists() -> None:
    """Demanding an exception after a lawful refusal is Escalation."""
    state = {
        "policy_decision": {
            "escalation_trigger": "lawful_refusal",
            "customer_insists_after_refusal": True,
        }
    }
    assert route_after_worker(state) == "escalation"


def test_route_after_worker_still_honors_requires_human() -> None:
    """Engine-owned high-value / inspection gates still pause the graph."""
    assert (
        route_after_worker({"policy_decision": {"requires_human": True}}) == "escalation"
    )
