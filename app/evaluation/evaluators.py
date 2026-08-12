"""Evaluation evaluators."""

from typing import Any


def evaluate_intent(predicted: str, expected: str) -> dict[str, Any]:
    """Evaluate intent classification accuracy."""
    passed = predicted == expected
    return {
        "name": "intent_accuracy",
        "passed": passed,
        "expected": expected,
        "predicted": predicted,
    }


def evaluate_escalation(predicted: bool, expected: bool) -> dict[str, Any]:
    """Evaluate escalation decision."""
    passed = predicted == expected
    return {
        "name": "escalation_accuracy",
        "passed": passed,
        "expected": expected,
        "predicted": predicted,
    }


def evaluate_keywords(answer: str, keywords: list[str]) -> dict[str, Any]:
    """Evaluate if answer contains expected keywords."""
    if not keywords:
        return {"name": "keyword_coverage", "passed": True, "keywords": keywords}
    lowered = answer.lower()
    found = [kw for kw in keywords if kw.lower() in lowered]
    passed = len(found) >= max(1, len(keywords) // 2)
    return {
        "name": "keyword_coverage",
        "passed": passed,
        "keywords": keywords,
        "found": found,
    }


def evaluate_groundedness(answer: str, context: list[dict[str, Any]]) -> dict[str, Any]:
    """Simple groundedness check against retrieved context."""
    if not context:
        return {"name": "groundedness", "passed": True, "overlap": 0.0}
    context_text = " ".join(item.get("content", "") for item in context).lower()
    answer_words = set(answer.lower().split())
    context_words = set(context_text.split())
    overlap = len(answer_words & context_words) / max(len(answer_words), 1)
    passed = overlap >= 0.05 or len(context) == 0
    return {"name": "groundedness", "passed": passed, "overlap": overlap}
