"""Knowledge-base path helpers used by ingestion."""

from pathlib import Path


def infer_domain(path: Path) -> str:
    """Infer retrieval domain from the TechStore KB tree."""
    posix = path.as_posix().lower()
    if "/policies/refund" in posix or "/policies/payment" in posix or "/faq/payments" in posix:
        return "billing"
    if "/policies/warranty" in posix:
        return "billing"
    if (
        "/policies/shipping" in posix
        or "/policies/return" in posix
        or "/faq/shipping" in posix
        or "/faq/returns" in posix
    ):
        return "logistics"
    if "/policies/account" in posix or "/procedures/identity" in posix:
        return "account"
    if "/procedures/refund" in posix:
        return "billing"
    return "general"


def should_ingest(path: Path, include_injection: bool) -> bool:
    """Skip the quarantined injection corpus unless explicitly enabled."""
    if "_eval_injection" in path.parts:
        return include_injection
    return True
