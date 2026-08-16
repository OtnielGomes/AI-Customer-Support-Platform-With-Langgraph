"""Evaluation metrics aggregation."""

from typing import Any


def aggregate_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate evaluation results into metrics."""
    if not results:
        return {"total": 0, "passed": 0, "pass_rate": 0.0, "by_metric": {}}

    metric_counts: dict[str, dict[str, int]] = {}
    for result in results:
        for evaluation in result.get("evaluations", []):
            name = evaluation["name"]
            metric_counts.setdefault(name, {"passed": 0, "total": 0})
            metric_counts[name]["total"] += 1
            if evaluation.get("passed"):
                metric_counts[name]["passed"] += 1

    by_metric = {
        name: {
            "passed": counts["passed"],
            "total": counts["total"],
            "pass_rate": counts["passed"] / counts["total"] if counts["total"] else 0.0,
        }
        for name, counts in metric_counts.items()
    }

    total_cases = len(results)
    passed_cases = sum(1 for r in results if r.get("passed"))
    return {
        "total": total_cases,
        "passed": passed_cases,
        "pass_rate": passed_cases / total_cases if total_cases else 0.0,
        "by_metric": by_metric,
    }


THRESHOLDS = {
    "intent_accuracy": 0.8,
    "escalation_accuracy": 0.7,
    "keyword_coverage": 0.6,
    "groundedness": 0.5,
    "tool_call_accuracy": 0.7,
    "policy_compliance": 0.8,
    "unauthorized_action": 1.0,
}


def check_thresholds(aggregated: dict[str, Any]) -> dict[str, bool]:
    """Check if metrics meet baseline thresholds."""
    results: dict[str, bool] = {}
    for metric, threshold in THRESHOLDS.items():
        metric_data = aggregated.get("by_metric", {}).get(metric, {})
        pass_rate = metric_data.get("pass_rate", 0.0)
        results[metric] = pass_rate >= threshold
    return results
