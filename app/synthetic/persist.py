"""Persist a generated World into PostgreSQL and export scenario fixtures."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_run import AgentEvent, AgentRun
from app.models.customer import Customer
from app.models.enums import (
    AccountStatus,
    CustomerTier,
    InspectionStatus,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    ProductCategory,
    RefundStatus,
    ReturnReason,
    ReturnStatus,
    ShipmentStatus,
)
from app.models.order import Order, OrderItem
from app.models.payment import Payment
from app.models.product import Product
from app.models.refund import Refund
from app.models.resolution import Resolution
from app.models.return_request import ReturnRequest
from app.models.shipment import Shipment
from app.models.synthetic_scenario import SyntheticScenario
from app.models.ticket import Ticket, TicketIntent, TicketStatus
from app.models.ticket_message import TicketMessage, TicketMessageRole
from app.synthetic.graph import DEMO_SHOWCASE_EMAIL, DEMO_SHOWCASE_NAME
from app.synthetic.records import World

logger = logging.getLogger(__name__)

FIXTURES_PATH = Path("data/fixtures/scenarios.json")
DEMO_LOGINS_PATH = Path("data/fixtures/demo_logins.json")

CHECKPOINT_TABLES = ("checkpoint_writes", "checkpoint_blobs", "checkpoints")

OPERATIONAL_TABLES = (
    AgentEvent,
    TicketMessage,
    AgentRun,
    Resolution,
    SyntheticScenario,
    Ticket,
    Refund,
    ReturnRequest,
    Shipment,
    Payment,
    OrderItem,
    Order,
    Product,
)


async def replace_operational_data(session: AsyncSession) -> None:
    """Delete operational synthetic rows, keeping kb_chunks."""
    for table in CHECKPOINT_TABLES:
        exists = await session.execute(text("SELECT to_regclass(:name)"), {"name": table})
        if exists.scalar():
            await session.execute(text(f"DELETE FROM {table}"))
    for model in OPERATIONAL_TABLES:
        await session.execute(delete(model))
    await session.execute(delete(Customer))
    await session.flush()


async def persist_world(session: AsyncSession, world: World) -> None:
    """Insert the generated world. Caller commits."""
    session.add_all(
        [
            Product(
                id=item.id,
                public_id=item.public_id,
                sku=item.sku,
                name=item.name,
                category=ProductCategory(item.category),
                unit_price=item.unit_price,
                final_sale=item.final_sale,
                warranty_days=item.warranty_days,
                active=item.active,
            )
            for item in world.products
        ]
    )
    session.add_all(
        [
            Customer(
                id=item.id,
                public_id=item.public_id,
                name=item.name,
                email=item.email,
                phone=item.phone,
                customer_tier=CustomerTier(item.customer_tier),
                account_status=AccountStatus(item.account_status),
                created_at=item.created_at,
            )
            for item in world.customers
        ]
    )
    await session.flush()
    session.add_all(
        [
            Order(
                id=item.id,
                public_id=item.public_id,
                customer_id=item.customer_id,
                status=OrderStatus(item.status),
                total_amount=item.total_amount,
                currency=item.currency,
                created_at=item.created_at,
                estimated_delivery=item.estimated_delivery,
                actual_delivery=item.actual_delivery,
            )
            for item in world.orders
        ]
    )
    await session.flush()
    session.add_all(
        [
            OrderItem(
                id=item.id,
                public_id=item.public_id,
                order_id=item.order_id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=item.line_total,
            )
            for item in world.order_items
        ]
    )
    session.add_all(
        [
            Payment(
                id=item.id,
                public_id=item.public_id,
                order_id=item.order_id,
                status=PaymentStatus(item.status),
                amount=item.amount,
                payment_method=PaymentMethod(item.payment_method),
                transaction_id=item.transaction_id,
                created_at=item.created_at,
            )
            for item in world.payments
        ]
    )
    session.add_all(
        [
            Shipment(
                id=item.id,
                public_id=item.public_id,
                order_id=item.order_id,
                carrier=item.carrier,
                tracking_code=item.tracking_code,
                status=ShipmentStatus(item.status),
                shipped_at=item.shipped_at,
                estimated_delivery=item.estimated_delivery,
                delivered_at=item.delivered_at,
                customer_received=item.customer_received,
            )
            for item in world.shipments
        ]
    )
    await session.flush()
    session.add_all(
        [
            ReturnRequest(
                id=item.id,
                public_id=item.public_id,
                order_id=item.order_id,
                customer_id=item.customer_id,
                reason=ReturnReason(item.reason),
                status=ReturnStatus(item.status),
                requested_at=item.requested_at,
                approved_at=item.approved_at,
                inspection_status=InspectionStatus(item.inspection_status),
            )
            for item in world.returns
        ]
    )
    await session.flush()
    session.add_all(
        [
            Refund(
                id=item.id,
                public_id=item.public_id,
                order_id=item.order_id,
                return_id=item.return_id,
                payment_id=item.payment_id,
                amount=item.amount,
                status=RefundStatus(item.status),
                reason=item.reason,
                requires_human_approval=item.requires_human_approval,
                created_at=item.created_at,
            )
            for item in world.refunds
        ]
    )
    session.add_all(
        [
            Ticket(
                id=item.id,
                customer_id=item.customer_id,
                order_id=item.order_id,
                subject=item.subject,
                description=item.description,
                status=TicketStatus(item.status),
                intent=TicketIntent(item.intent) if item.intent else None,
                created_at=item.created_at,
                last_message_at=item.created_at,
            )
            for item in world.tickets
        ]
    )
    session.add_all(
        [
            TicketMessage(
                ticket_id=item.id,
                role=TicketMessageRole.CUSTOMER,
                content=item.description,
                created_at=item.created_at,
            )
            for item in world.tickets
            if item.description
        ]
    )
    session.add_all(
        [
            SyntheticScenario(
                id=item.id,
                kind=item.kind,
                customer_id=item.customer_id,
                order_id=item.order_id,
                payload=item.payload,
                user_message_pt=item.user_message_pt,
                expected_intent=item.expected_intent,
                expected_resolution=item.expected_resolution,
                requires_human=item.requires_human,
            )
            for item in world.scenarios
        ]
    )
    await session.flush()
    logger.info(
        "Persisted %s customers, %s orders, %s scenarios",
        len(world.customers),
        len(world.orders),
        len(world.scenarios),
    )


def export_scenarios(world: World, path: Path | None = None) -> Path:
    """Write evaluation fixtures mapping scenario ids to public ids."""
    target = path or FIXTURES_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    customers = {item.id: item for item in world.customers}
    orders = {item.id: item for item in world.orders}
    payload = []
    for scenario in world.scenarios:
        customer = customers[scenario.customer_id]
        order = orders.get(scenario.order_id) if scenario.order_id else None
        payload.append(
            {
                "id": scenario.id,
                "kind": scenario.kind,
                "customer_public_id": customer.public_id,
                "customer_email": customer.email,
                "order_public_id": order.public_id if order else None,
                "user_message": scenario.user_message_pt,
                "expected_intent": scenario.expected_intent,
                "expected_tools": scenario.expected_tools,
                "expected_policy": scenario.expected_policy,
                "expected_resolution": scenario.expected_resolution,
                "requires_human": scenario.requires_human,
            }
        )
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    logger.info("Wrote %s fixtures to %s", len(payload), target)
    _export_demo_logins(world, customers, orders, target.parent / "demo_logins.json")
    _export_manual_test_guide(world, customers, orders, target.parent / "demo_manual_tests.md")
    return target


def _export_demo_logins(
    world: World,
    customers: dict,
    orders: dict,
    path: Path,
) -> None:
    """Write portal login emails keyed by scenario for local demos."""
    orders_by_customer: dict = {}
    for order in world.orders:
        orders_by_customer.setdefault(order.customer_id, []).append(order.public_id)
    rows = []
    for scenario in world.scenarios:
        customer = customers[scenario.customer_id]
        order = orders.get(scenario.order_id) if scenario.order_id else None
        rows.append(
            {
                "email": customer.email,
                "name": customer.name,
                "customer_public_id": customer.public_id,
                "scenario_id": scenario.id,
                "kind": scenario.kind,
                "order_public_id": order.public_id if order else None,
                "order_count": len(orders_by_customer.get(customer.id, [])),
            }
        )
    # Unique by email, first scenario wins for the README table.
    seen: set[str] = set()
    unique = []
    for row in rows:
        if row["email"] in seen:
            continue
        seen.add(row["email"])
        unique.append(row)
    path.write_text(json.dumps(unique, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    logger.info("Wrote %s demo logins to %s", len(unique), path)


def _export_manual_test_guide(
    world: World,
    customers: dict,
    orders: dict,
    path: Path,
) -> None:
    """Write a portal checklist for the dedicated demo customer."""
    if not any(item.email.lower() == DEMO_SHOWCASE_EMAIL for item in customers.values()):
        path.write_text("# Demo customer was not generated.\n", encoding="utf-8")
        return
    rows = [
        scenario
        for scenario in world.scenarios
        if scenario.id.startswith("SCN-DEMO-")
    ]
    lines = [
        "# Demo customer — manual agent tests",
        "",
        f"Portal login: `{DEMO_SHOWCASE_EMAIL}` ({DEMO_SHOWCASE_NAME}).",
        "Open a new conversation, pick the order, and paste the suggested message.",
        "",
        "| Scenario | Order | Kind | Message | Expected tools |"
        " Policy | Expected resolution | Human? |",
        "|----------|-------|------|---------|----------------|"
        "--------|---------------------|--------|",
    ]
    for scenario in rows:
        order = orders.get(scenario.order_id) if scenario.order_id else None
        order_id = order.public_id if order else "—"
        tools = ", ".join(scenario.expected_tools) or "—"
        human = "yes" if scenario.requires_human else "no"
        message = scenario.user_message_pt.replace("|", "/")
        row = (
            f"| `{scenario.id}` | `{order_id}` | `{scenario.kind}` | {message} |"
            f" `{tools}` | `{scenario.expected_policy}` |"
            f" `{scenario.expected_resolution}` | {human} |"
        )
        lines.append(row)
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Wrote %s manual demo cases to %s", len(rows), path)


async def operational_row_count(session: AsyncSession) -> int:
    """Return how many customers currently exist."""
    result = await session.execute(select(Customer.id))
    return len(result.scalars().all())
