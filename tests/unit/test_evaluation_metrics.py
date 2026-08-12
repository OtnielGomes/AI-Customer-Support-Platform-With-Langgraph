"""Unit tests for evaluation metrics."""

from app.evaluation.metrics import aggregate_results, check_thresholds


def test_aggregate_results() -> None:
    """Should compute pass rates."""
    results = [
        {
            "passed": True,
            "evaluations": [
                {"name": "intent_accuracy", "passed": True},
                {"name": "escalation_accuracy", "passed": True},
            ],
        },
        {
            "passed": False,
            "evaluations": [
                {"name": "intent_accuracy", "passed": False},
                {"name": "escalation_accuracy", "passed": True},
            ],
        },
    ]
    agg = aggregate_results(results)
    assert agg["total"] == 2
    assert agg["passed"] == 1
    assert agg["by_metric"]["intent_accuracy"]["pass_rate"] == 0.5


def test_check_thresholds() -> None:
    """Should compare against baseline thresholds."""
    agg = {
        "by_metric": {
            "intent_accuracy": {"pass_rate": 0.9},
            "escalation_accuracy": {"pass_rate": 0.5},
        }
    }
    checks = check_thresholds(agg)
    assert checks["intent_accuracy"] is True
    assert checks["escalation_accuracy"] is False
