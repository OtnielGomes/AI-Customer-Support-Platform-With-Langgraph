"""In-memory records produced by the synthetic generator (not ORM)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass
class ProductRecord:
    """Catalog product."""

    id: uuid.UUID
    public_id: str
    sku: str
    name: str
    category: str
    unit_price: Decimal
    final_sale: bool
    warranty_days: int
    active: bool = True


@dataclass
class CustomerRecord:
    """Customer account."""

    id: uuid.UUID
    public_id: str
    name: str
    email: str
    phone: str | None
    customer_tier: str
    account_status: str
    created_at: datetime


@dataclass
class OrderItemRecord:
    """Order line."""

    id: uuid.UUID
    public_id: str
    order_id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    unit_price: Decimal
    line_total: Decimal


@dataclass
class OrderRecord:
    """Purchase order."""

    id: uuid.UUID
    public_id: str
    customer_id: uuid.UUID
    status: str
    total_amount: Decimal
    currency: str
    created_at: datetime
    estimated_delivery: datetime | None
    actual_delivery: datetime | None


@dataclass
class PaymentRecord:
    """Payment against an order."""

    id: uuid.UUID
    public_id: str
    order_id: uuid.UUID
    status: str
    amount: Decimal
    payment_method: str
    transaction_id: str
    created_at: datetime


@dataclass
class ShipmentRecord:
    """Shipment for an order."""

    id: uuid.UUID
    public_id: str
    order_id: uuid.UUID
    carrier: str
    tracking_code: str
    status: str
    shipped_at: datetime | None
    estimated_delivery: datetime | None
    delivered_at: datetime | None
    customer_received: bool | None


@dataclass
class ReturnRecord:
    """Return request."""

    id: uuid.UUID
    public_id: str
    order_id: uuid.UUID
    customer_id: uuid.UUID
    reason: str
    status: str
    requested_at: datetime
    approved_at: datetime | None
    inspection_status: str


@dataclass
class RefundRecord:
    """Refund request."""

    id: uuid.UUID
    public_id: str
    order_id: uuid.UUID
    return_id: uuid.UUID | None
    payment_id: uuid.UUID | None
    amount: Decimal
    status: str
    reason: str
    requires_human_approval: bool
    created_at: datetime


@dataclass
class TicketRecord:
    """Support ticket attached to a customer/order."""

    id: uuid.UUID
    customer_id: uuid.UUID
    order_id: uuid.UUID | None
    subject: str
    description: str
    status: str
    intent: str | None
    created_at: datetime


@dataclass
class ScenarioRecord:
    """Labeled evaluation scenario."""

    id: str
    kind: str
    customer_id: uuid.UUID
    order_id: uuid.UUID | None
    payload: dict[str, Any]
    user_message_pt: str
    expected_intent: str
    expected_resolution: str
    requires_human: bool
    expected_tools: list[str] = field(default_factory=list)
    expected_policy: str = ""


@dataclass
class World:
    """Complete in-memory TechStore snapshot."""

    products: list[ProductRecord] = field(default_factory=list)
    customers: list[CustomerRecord] = field(default_factory=list)
    orders: list[OrderRecord] = field(default_factory=list)
    order_items: list[OrderItemRecord] = field(default_factory=list)
    payments: list[PaymentRecord] = field(default_factory=list)
    shipments: list[ShipmentRecord] = field(default_factory=list)
    returns: list[ReturnRecord] = field(default_factory=list)
    refunds: list[RefundRecord] = field(default_factory=list)
    tickets: list[TicketRecord] = field(default_factory=list)
    scenarios: list[ScenarioRecord] = field(default_factory=list)
