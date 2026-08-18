"""Input/output guardrails."""

import re

INJECTION_PATTERNS = [
    r"ignore\s+previous\s+instructions",
    r"ignore\s+a\s+pol",
    r"disregard\s+all",
    r"system\s+prompt",
    r"you\s+are\s+now",
    r"eu\s+sou\s+administrador",
    r"i\s+am\s+(an?\s+)?admin",
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


_ESCALATION_REASON_RE = re.compile(
    r"(?:\n+\s*)?Escalation reason:\s*.*$",
    re.IGNORECASE | re.DOTALL,
)


def normalize_markdown(text: str) -> str:
    """Strip headings, tables, and decorative bold from assistant replies."""
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("|") and stripped.endswith("|"):
            continue
        if stripped.startswith("#"):
            line = re.sub(r"^#{1,6}\s*", "", stripped)
        lines.append(line)
    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\*\*(.+?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"__(.+?)__", r"\1", cleaned)
    return cleaned.strip()


def sanitize_customer_answer(text: str) -> str:
    """Clean assistant text before it is persisted or shown to the customer."""
    cleaned = normalize_markdown(text)
    cleaned = _ESCALATION_REASON_RE.sub("", cleaned).strip()
    return _collapse_repeated_answer(cleaned)


def _collapse_repeated_answer(text: str) -> str:
    """Collapse an identical reply pasted two or more times."""
    if not text:
        return text
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    collapsed_parts: list[str] = []
    for paragraph in paragraphs:
        unit = _collapse_concatenated_copy(paragraph)
        if not collapsed_parts or collapsed_parts[-1] != unit:
            collapsed_parts.append(unit)
    return "\n\n".join(collapsed_parts)


def _collapse_concatenated_copy(text: str) -> str:
    """If ``text`` is the same string repeated 2-4 times, keep one copy."""
    length = len(text)
    if length < 40:
        return text
    for parts in range(2, 5):
        if length % parts != 0:
            continue
        size = length // parts
        if size < 20:
            continue
        unit = text[:size]
        if unit * parts == text:
            return unit
    return text


def validate_output(
    text: str,
    refund_tool_success: bool = False,
    refund_executed: bool = False,
) -> str:
    """Validate model output before returning to user."""
    del refund_tool_success
    cleaned = sanitize_customer_answer(text)
    if REFUND_CLAIM_PATTERN.search(cleaned) and not refund_executed:
        raise GuardrailViolation("Output claims refund without executed refund")
    if len(cleaned) > 20000:
        raise GuardrailViolation("Output exceeds maximum length")
    return cleaned
