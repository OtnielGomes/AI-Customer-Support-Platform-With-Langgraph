"""Graph routing honors the closed Escalation catalog and ADR-0011."""

from app.graph.edges import route_after_supervisor, route_after_worker


def test_unknown_intent_routes_to_logistics() -> None:
    """Unknown intent with no catalog trigger is Order Facts, not Escalation."""
    assert (
        route_after_supervisor({"intent": "unknown", "confidence": 0.9}) == "logistics"
    )


def test_unknown_intent_low_confidence_routes_to_logistics() -> None:
    """Unknown stays with logistics even when the classifier is unsure."""
    assert (
        route_after_supervisor({"intent": "unknown", "confidence": 0.1}) == "logistics"
    )


def test_low_confidence_billing_routes_to_billing() -> None:
    """A known domain still goes to that worker below the old 0.7 threshold."""
    assert route_after_supervisor({"intent": "billing", "confidence": 0.3}) == "billing"


def test_low_confidence_logistics_routes_to_logistics() -> None:
    """Low-confidence logistics is still logistics, not Escalation."""
    assert (
        route_after_supervisor({"intent": "logistics", "confidence": 0.3}) == "logistics"
    )


def test_low_confidence_account_routes_to_account() -> None:
    """Low-confidence account is still account, not a logistics dump."""
    assert route_after_supervisor({"intent": "account", "confidence": 0.3}) == "account"


def test_high_confidence_known_domains_route_to_workers() -> None:
    """High-confidence billing, logistics, and account still reach those workers."""
    assert route_after_supervisor({"intent": "billing", "confidence": 0.9}) == "billing"
    assert route_after_supervisor({"intent": "logistics", "confidence": 0.9}) == "logistics"
    assert route_after_supervisor({"intent": "account", "confidence": 0.9}) == "account"


def test_catalog_trigger_routes_to_escalation_even_for_billing() -> None:
    """A catalog hit pauses even when intent is a known domain."""
    state = {
        "intent": "billing",
        "confidence": 0.9,
        "policy_decision": {"escalation_trigger": "fraud"},
    }
    assert route_after_supervisor(state) == "escalation"


def test_requires_human_after_supervisor_routes_to_escalation() -> None:
    """Engine requires_human still pauses after the supervisor."""
    state = {
        "intent": "billing",
        "confidence": 0.9,
        "policy_decision": {"requires_human": True},
    }
    assert route_after_supervisor(state) == "escalation"


def test_needs_human_already_set_routes_to_escalation() -> None:
    """Unusable identity loaded before the supervisor still Escalation."""
    state = {
        "intent": "logistics",
        "confidence": 0.9,
        "needs_human": True,
    }
    assert route_after_supervisor(state) == "escalation"


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
