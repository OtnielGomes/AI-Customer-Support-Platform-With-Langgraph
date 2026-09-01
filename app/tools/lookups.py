"""Shared lookup helpers for scoped operational tools."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.customer import Customer
from app.models.order import Order, OrderItem
from app.models.payment import Payment
from app.models.product import Product
from app.models.return_request import ReturnRequest
from app.models.shipment import Shipment
from app.policies.loader import load_company_config
from app.services.order_summary import order_to_dict as serialize_order
from app.synthetic.clock import company_timezone, resolve_simulation_now
from app.tools.context import ToolContext


def parse_uuid(value: str) -> uuid.UUID | None:
    """Parse a UUID string, returning None on failure."""
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return None


async def load_customer(session: AsyncSession, identifier: str) -> Customer | None:
    """Load a customer by UUID or public_id."""
    customer_uuid = parse_uuid(identifier)
    stmt = select(Customer)
    if customer_uuid is not None:
        stmt = stmt.where(Customer.id == customer_uuid)
    else:
        stmt = stmt.where(Customer.public_id == identifier)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def load_order(session: AsyncSession, identifier: str) -> Order | None:
    """Load an order by UUID or public_id, with items and product."""
    order_uuid = parse_uuid(identifier)
    stmt = select(Order).options(
        selectinload(Order.items).selectinload(OrderItem.product),
        selectinload(Order.payments),
    )
    if order_uuid is not None:
        stmt = stmt.where(Order.id == order_uuid)
    else:
        stmt = stmt.where(Order.public_id == identifier)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def scoped_to_customer(context: ToolContext, customer_id: uuid.UUID) -> bool:
    """Return True when the entity belongs to the ticket customer (if bound)."""
    if context.customer_id is None:
        return True
    return customer_id == context.customer_id


async def list_customer_orders(session: AsyncSession, customer_id: uuid.UUID) -> list[Order]:
    """Load orders for one customer, newest first, with items and payments."""
    result = await session.execute(
        select(Order)
        .options(
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.payments),
        )
        .where(Order.customer_id == customer_id)
        .order_by(Order.created_at.desc())
    )
    return list(result.scalars().unique().all())


def order_to_dict(order: Order, *, include_items: bool = False) -> dict[str, Any]:
    """Serialize an order header, optionally with line items."""
    return serialize_order(order, include_items=include_items)


def customer_to_dict(customer: Customer) -> dict[str, Any]:
    """Serialize a customer without secrets."""
    return {
        "id": str(customer.id),
        "public_id": customer.public_id,
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
        "customer_tier": customer.customer_tier.value,
        "account_status": customer.account_status.value,
    }


def days_since_delivery(order: Order) -> int | None:
    """Whole days between delivery and the simulation clock."""
    delivered = order.actual_delivery
    if delivered is None:
        return None
    try:
        from app.config import get_settings

        as_of = get_settings().simulation_as_of
        now = resolve_simulation_now(load_company_config(), as_of=as_of or None)
    except Exception:
        now = datetime.now(company_timezone(load_company_config()))
    if delivered.tzinfo is None:
        delivered = delivered.replace(tzinfo=now.tzinfo)
    return max(0, (now - delivered).days)


async def load_payments(session: AsyncSession, order_id: uuid.UUID) -> list[Payment]:
    """Load payments for an order."""
    result = await session.execute(select(Payment).where(Payment.order_id == order_id))
    return list(result.scalars().all())


async def load_shipment(session: AsyncSession, order_id: uuid.UUID) -> Shipment | None:
    """Load the v1 shipment for an order."""
    result = await session.execute(select(Shipment).where(Shipment.order_id == order_id))
    return result.scalar_one_or_none()


async def load_returns(session: AsyncSession, order_id: uuid.UUID) -> list[ReturnRequest]:
    """Load return requests for an order."""
    result = await session.execute(select(ReturnRequest).where(ReturnRequest.order_id == order_id))
    return list(result.scalars().all())


def primary_product(order: Order) -> Product | None:
    """Return the first line-item product if loaded."""
    if not order.items:
        return None
    return order.items[0].product
