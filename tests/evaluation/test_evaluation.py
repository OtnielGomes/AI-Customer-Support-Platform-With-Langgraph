"""Evaluation test wrappers."""

from app.evaluation.datasets.nexa_cases import NEXA_DATASET
from app.evaluation.evaluators import (
    evaluate_escalation,
    evaluate_intent,
    evaluate_policy_compliance,
    evaluate_tool_calls,
    evaluate_unauthorized_action,
)
from app.evaluation.metrics import aggregate_results, check_thresholds


def test_nexa_dataset_structure() -> None:
    """Nexa fixtures should cover the required groups and negative tests."""
    assert len(NEXA_DATASET) >= 15
    kinds = {case["kind"] for case in NEXA_DATASET}
    for required in {
        "double_payment",
        "delayed_shipment",
        "delivered_missing",
        "refund_outside_window",
        "defective_warranty",
        "high_value_refund",
        "cancel_after_ship",
        "fraud_risk",
        "final_sale",
        "gold_tier",
        "negative_security",
    }:
        assert required in kinds
    for case in NEXA_DATASET:
        assert case["id"]
        assert case["message"]
        assert "expected_intent" in case


def test_evaluators_on_duplicate_payment_case() -> None:
    """Evaluators should score a well-behaved duplicate-charge run."""
    case = next(item for item in NEXA_DATASET if item["kind"] == "double_payment")
    evaluations = [
        evaluate_intent("billing", case["expected_intent"]),
        evaluate_escalation(False, case["should_escalate"]),
        evaluate_tool_calls(["get_order", "get_payments"], case["expected_tools"]),
        evaluate_policy_compliance(
            {"eligible": True, "requires_human": False},
            case["expected_resolution"],
            case["requires_human"],
        ),
        evaluate_unauthorized_action(
            ["get_order", "get_payments"],
            [{"tool": "get_order", "result": {"public_id": "ORD-01001"}}],
            case["expected_resolution"],
        ),
    ]
    result = {"passed": all(item["passed"] for item in evaluations), "evaluations": evaluations}
    agg = aggregate_results([result])
    assert agg["total"] == 1
    assert result["passed"]


def test_unauthorized_action_fails_on_security_write() -> None:
    """A refused security case must not successfully create a refund."""
    case = next(item for item in NEXA_DATASET if item["id"] == "SCN-NEG-HUGE-REFUND")
    evaluation = evaluate_unauthorized_action(
        ["create_refund_request"],
        [{"tool": "create_refund_request", "result": {"status": "requested"}}],
        case["expected_resolution"],
    )
    assert evaluation["passed"] is False


def test_thresholds_defined() -> None:
    """All threshold metrics should be checkable."""
    agg = aggregate_results([])
    checks = check_thresholds(agg)
    assert "unauthorized_action" in checks
    assert isinstance(checks, dict)
