"""Evaluation test wrappers."""

from app.evaluation.datasets.billing_cases import BILLING_DATASET
from app.evaluation.evaluators import (
    evaluate_escalation,
    evaluate_intent,
    evaluate_keywords,
)
from app.evaluation.metrics import aggregate_results, check_thresholds


def test_billing_dataset_structure() -> None:
    """Dataset cases should have required fields."""
    for case in BILLING_DATASET:
        assert "id" in case
        assert "message" in case
        assert "expected_intent" in case
        assert "should_escalate" in case


def test_evaluators_on_sample_case() -> None:
    """Evaluators should run on synthetic results."""
    case = BILLING_DATASET[0]
    evaluations = [
        evaluate_intent("billing", case["expected_intent"]),
        evaluate_escalation(False, case["should_escalate"]),
        evaluate_keywords("Refund for INV-1001 approved", case["keywords"]),
    ]
    result = {
        "passed": all(e["passed"] for e in evaluations),
        "evaluations": evaluations,
    }
    agg = aggregate_results([result])
    assert agg["total"] == 1


def test_thresholds_defined() -> None:
    """All threshold metrics should be checkable."""
    agg = aggregate_results([])
    checks = check_thresholds(agg)
    assert isinstance(checks, dict)
