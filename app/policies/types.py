"""Pydantic decision types for the policy engine."""

from decimal import Decimal

from pydantic import BaseModel, Field


class RefundDecision(BaseModel):
    """Deterministic refund eligibility outcome."""

    eligible: bool
    requires_human: bool
    reasons: list[str] = Field(default_factory=list)
    restocking_fee_rate: Decimal | None = None
    max_amount: Decimal | None = None
    original_payment_method_only: bool = True
    inspection_required: bool = False
    policy_ids: list[str] = Field(default_factory=list)


class CancelDecision(BaseModel):
    """Deterministic cancellation eligibility outcome."""

    eligible: bool
    requires_human: bool = False
    reasons: list[str] = Field(default_factory=list)
    policy_ids: list[str] = Field(default_factory=list)
