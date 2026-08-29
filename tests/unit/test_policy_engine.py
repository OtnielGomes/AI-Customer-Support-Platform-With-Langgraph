"""Table-driven policy engine tests (no LLM)."""

from decimal import Decimal

import pytest

from app.policies.engine import can_cancel, can_refund, should_escalate
from app.policies.loader import load_company_config


@pytest.fixture
def company() -> dict:
    """Load canonical company configuration."""
    return load_company_config()


def test_preference_within_window_low_value(company: dict) -> None:
    """Delivered 10d, preference, R$200 is eligible without human approval."""
    decision = can_refund(
        days_since_delivery=10,
        amount=Decimal("200.00"),
        product_category="accessories",
        final_sale=False,
        reason="customer_preference",
        identity_verified=True,
        warranty_days=90,
        company=company,
    )
    assert decision.eligible is True
    assert decision.requires_human is False
    assert decision.restocking_fee_rate == Decimal("0.10")


def test_preference_outside_window(company: dict) -> None:
    """Delivered 35d preference is denied."""
    decision = can_refund(
        days_since_delivery=35,
        amount=Decimal("200.00"),
        product_category="accessories",
        final_sale=False,
        reason="customer_preference",
        identity_verified=True,
        warranty_days=90,
        company=company,
    )
    assert decision.eligible is False
    assert "OUTSIDE_WINDOW" in decision.reasons


def test_defective_outside_refund_inside_warranty(company: dict) -> None:
    """Defective laptop after 35 days still has a warranty path."""
    decision = can_refund(
        days_since_delivery=35,
        amount=Decimal("3499.00"),
        product_category="laptops",
        final_sale=False,
        reason="defective_product",
        identity_verified=True,
        warranty_days=365,
        company=company,
    )
    assert decision.eligible is True
    assert "WARRANTY_EXCEPTION" in decision.reasons
    assert "warranty_policy" in decision.policy_ids
    assert decision.requires_human is True


def test_high_value_requires_human(company: dict) -> None:
    """Amounts above R$1000 require human approval even when eligible."""
    decision = can_refund(
        days_since_delivery=10,
        amount=Decimal("3500.00"),
        product_category="laptops",
        final_sale=False,
        reason="customer_preference",
        identity_verified=True,
        warranty_days=365,
        company=company,
    )
    assert decision.eligible is True
    assert decision.requires_human is True


def test_final_sale_preference_denied(company: dict) -> None:
    """Final-sale goods cannot be refunded for preference."""
    decision = can_refund(
        days_since_delivery=5,
        amount=Decimal("79.90"),
        product_category="accessories",
        final_sale=True,
        reason="customer_preference",
        identity_verified=True,
        warranty_days=90,
        company=company,
    )
    assert decision.eligible is False
    assert "FINAL_SALE" in decision.reasons


def test_identity_not_verified_does_not_execute(company: dict) -> None:
    """Unverified identity never auto-executes a refund."""
    decision = can_refund(
        days_since_delivery=5,
        amount=Decimal("200.00"),
        product_category="accessories",
        final_sale=False,
        reason="customer_preference",
        identity_verified=False,
        warranty_days=90,
        company=company,
    )
    assert decision.eligible is False
    assert decision.requires_human is True
    assert "IDENTITY_REQUIRED" in decision.reasons


def test_duplicate_charge(company: dict) -> None:
    """Verified duplicate charges skip the return window and restocking fee."""
    decision = can_refund(
        days_since_delivery=40,
        amount=Decimal("899.90"),
        product_category="headphones",
        final_sale=False,
        reason="customer_preference",
        identity_verified=True,
        warranty_days=90,
        duplicate_charge=True,
        company=company,
    )
    assert decision.eligible is True
    assert "DUPLICATE_CHARGE" in decision.reasons
    assert decision.restocking_fee_rate == Decimal("0")
    assert decision.requires_human is False


def test_cancel_after_ship_denied(company: dict) -> None:
    """Shipped orders cannot be cancelled directly."""
    decision = can_cancel(
        shipment_status="in_transit",
        order_status="shipped",
        company=company,
    )
    assert decision.eligible is False
    assert decision.requires_human is False
    assert "SHIPPED_USE_RETURN" in decision.reasons


def test_cancel_before_ship_eligible(company: dict) -> None:
    """Unshipped orders may be cancelled without Escalation."""
    decision = can_cancel(
        shipment_status=None,
        order_status="processing",
        company=company,
    )
    assert decision.eligible is True
    assert decision.requires_human is False


def test_withdrawal_within_legal_window(company: dict) -> None:
    """CDC Withdrawal is eligible within 7 days of receipt."""
    decision = can_refund(
        days_since_delivery=5,
        amount=Decimal("200.00"),
        product_category="accessories",
        final_sale=False,
        reason="withdrawal",
        identity_verified=True,
        warranty_days=90,
        company=company,
    )
    assert decision.eligible is True
    assert decision.requires_human is False
    assert "WITHDRAWAL" in decision.reasons


def test_withdrawal_outside_legal_window_is_coded_refusal(company: dict) -> None:
    """Day 10 Withdrawal is refused in-thread, not Escalation."""
    decision = can_refund(
        days_since_delivery=10,
        amount=Decimal("200.00"),
        product_category="accessories",
        final_sale=False,
        reason="withdrawal",
        identity_verified=True,
        warranty_days=90,
        company=company,
    )
    assert decision.eligible is False
    assert decision.requires_human is False
    assert "OUTSIDE_WITHDRAWAL_WINDOW" in decision.reasons


@pytest.mark.parametrize(
    ("trigger", "insist", "escalate"),
    [
        ("delivered_but_missing", False, True),
        ("fraud", False, True),
        ("privacy_beyond_own_profile", False, True),
        ("product_technical_assistance", False, True),
        ("unusable_identity", False, True),
        ("policy_exception_demanded", False, True),
        ("lawful_refusal", False, False),
        ("lawful_refusal", True, True),
        ("order_tracking", False, False),
        ("payment_status", False, False),
    ],
)
def test_closed_escalation_catalog(
    trigger: str, insist: bool, escalate: bool
) -> None:
    """Escalation fires only for the closed catalog, not for tracking or first refusal."""
    decision = should_escalate(
        trigger=trigger, customer_insists_after_refusal=insist
    )
    assert decision.escalate is escalate
