"""Input/output guardrails."""

import re

INJECTION_PATTERNS = [
    r"ignore\s+previous\s+instructions",
    r"disregard\s+all",
    r"system\s+prompt",
    r"you\s+are\s+now",
]

REFUND_CLAIM_PATTERN = re.compile(
    r"\b(refund|reembolso)\s+(has\s+been|foi|was|está)\s+(processed|aprovado|approved)",
    re.IGNORECASE,
)


class GuardrailViolation(Exception):
    """Raised when content fails guardrail checks."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def sanitize_input(text: str) -> str:
    """Sanitize user input and detect prompt injection attempts."""
    cleaned = text.strip()
    lowered = cleaned.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lowered):
            raise GuardrailViolation("Potential prompt injection detected")
    if len(cleaned) > 10000:
        raise GuardrailViolation("Input exceeds maximum length")
    return cleaned


def validate_output(text: str, refund_tool_success: bool = False) -> str:
    """Validate model output before returning to user."""
    if REFUND_CLAIM_PATTERN.search(text) and not refund_tool_success:
        raise GuardrailViolation("Output claims refund without successful tool execution")
    if len(text) > 20000:
        raise GuardrailViolation("Output exceeds maximum length")
    return text
