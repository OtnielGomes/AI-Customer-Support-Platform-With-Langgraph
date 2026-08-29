"""Happy-path operational graph generation."""

from __future__ import annotations

import unicodedata
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.policies.loader import load_company_config
from app.synthetic.catalogs import catalog_slice, price, random_person_name
from app.synthetic.records import (
    CustomerRecord,
    OrderItemRecord,
    OrderRecord,
    PaymentRecord,
    ProductRecord,
    ShipmentRecord,
    TicketRecord,
    World,
)
from app.synthetic.rng import SeededRNG

PROFILES: dict[str, dict[str, int]] = {
    "demo": {
        "customers": 20,
        "products": 24,
        "orders": 40,
        "anomaly_copies": 1,
    },
    "v1": {
        "customers": 1000,
        "products": 80,
        "orders": 3000,
        "anomaly_copies": 3,
    },
    "load": {
        "customers": 10000,
        "products": 80,
        "orders": 25000,
        "anomaly_copies": 3,
    },
}

TIER_WEIGHTS = [("standard", 55), ("silver", 25), ("gold", 15), ("enterprise", 5)]
# Order statuses only — in_transit belongs on ShipmentStatus, not OrderStatus.
# Shipped orders get shipment_status=in_transit via add_order_bundle().
STATUS_WEIGHTS = [
    ("delivered", 55),
    ("shipped", 20),
    ("processing", 7),
    ("paid", 3),
    ("pending", 3),
    ("cancelled", 7),
    ("returned", 5),
]
DEFAULT_PAYMENT_METHODS = ["pix", "credit_card"]
EMAIL_DOMAINS = ("gmail.com", "outlook.com", "uol.com.br", "nexamail.com")
DEMO_LOGIN_EMAIL = "ana.costa@nexamail.com"
DEMO_LOGIN_NAME = "Ana Costa"
DEMO_SHOWCASE_EMAIL = "demo@test.com.br"
DEMO_SHOWCASE_NAME = "Demo Tester"


def load_company_yaml(path: Path | None = None) -> dict[str, Any]:
    """Load the TechStore world model."""
    return load_company_config(path)


def allowed_payment_methods(company: dict[str, Any]) -> list[str]:
    """Return v1.0 Payment Methods from the world model."""
    methods = company.get("payment", {}).get("methods")
    if isinstance(methods, list) and methods:
        return [str(item) for item in methods]
    return list(DEFAULT_PAYMENT_METHODS)


def simulation_now(company: dict[str, Any]) -> datetime:
    """Parse the frozen simulation clock."""
    return datetime.fromisoformat(company["simulation"]["now"])


def build_products(rng: SeededRNG, count: int) -> list[ProductRecord]:
    """Build the product catalog."""
    products: list[ProductRecord] = []
    for index, spec in enumerate(catalog_slice(count), start=1):
        products.append(
            ProductRecord(
                id=rng.uuid4(),
                public_id=f"PRD-{index:05d}",
                sku=spec["sku"],
                name=spec["name"],
                category=spec["category"],
                unit_price=price(spec["unit_price"]),
                final_sale=bool(spec["final_sale"]),
                warranty_days=int(spec["warranty_days"]),
            )
        )
    return products


def _slug_person(name: str) -> str:
    """ASCII email local-part from a display name."""
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return ".".join(part for part in normalized.lower().replace("'", "").split() if part)


def allocate_login_email(world: World, name: str, index: int) -> str:
    """Build a unique realistic login email for ``name``."""
    used = {item.email.lower() for item in world.customers}
    slug = _slug_person(name) or f"cliente{index:04d}"
    domain = EMAIL_DOMAINS[(index - 1) % len(EMAIL_DOMAINS)]
    candidate = f"{slug}@{domain}"
    suffix = 2
    while candidate.lower() in used:
        candidate = f"{slug}{suffix}@{domain}"
        suffix += 1
    return candidate


def build_customer(
    world: World,
    rng: SeededRNG,
    now: datetime,
    *,
    index: int,
    tier: str | None = None,
    status: str = "active",
    email: str | None = None,
    name: str | None = None,
) -> CustomerRecord:
    """Create one customer with a sequential public_id placeholder (reassigned later)."""
    person = name or random_person_name(rng)
    return CustomerRecord(
        id=rng.uuid4(),
        public_id=f"CUST-{index:05d}",
        name=person,
        email=email or allocate_login_email(world, person, index),
        phone=f"+55119{rng.randint(10000000, 99999999)}",
        customer_tier=tier or _weighted_tier(rng),
        account_status=status,
        created_at=now - timedelta(days=rng.randint(40, 400)),
    )


def _weighted_tier(rng: SeededRNG) -> str:
    labels, weights = zip(*TIER_WEIGHTS, strict=True)
    return rng.choices(list(labels), weights=list(weights), k=1)[0]


def _weighted_order_status(rng: SeededRNG) -> str:
    labels, weights = zip(*STATUS_WEIGHTS, strict=True)
    return rng.choices(list(labels), weights=list(weights), k=1)[0]


def add_order_bundle(
    world: World,
    rng: SeededRNG,
    now: datetime,
    company: dict[str, Any],
    customer: CustomerRecord,
    product: ProductRecord,
    *,
    status: str,
    created_at: datetime,
    quantity: int = 1,
    extra_paid_payment: bool = False,
    failed_payments: int = 0,
    payment_method: str | None = None,
    second_payment_method: str | None = None,
    shipment_status: str | None = None,
    estimated_offset_days: int | None = None,
    delivered_offset_days: int | None = None,
    customer_received: bool | None = None,
) -> OrderRecord:
    """Append an order with items, payments, and optional shipment."""
    order_index = len(world.orders) + 1001
    item_index = len(world.order_items) + 1
    pay_index = len(world.payments) + 1
    ship_index = len(world.shipments) + 1
    carriers = company["shipping"]["carriers"]
    allowed_methods = allowed_payment_methods(company)
    method = payment_method or rng.choice(allowed_methods)
    if method not in allowed_methods:
        method = allowed_methods[0]
    line_total = (product.unit_price * quantity).quantize(Decimal("0.01"))
    estimated = created_at + timedelta(days=estimated_offset_days or rng.randint(3, 12))
    delivered_at: datetime | None = None
    actual_delivery: datetime | None = None
    shipped_at: datetime | None = None

    ship_status = shipment_status
    if status in {"shipped", "delivered", "returned"} and ship_status is None:
        ship_status = "delivered" if status in {"delivered", "returned"} else "in_transit"
    if status == "cancelled":
        ship_status = None

    if ship_status and ship_status != "processing":
        shipped_at = created_at + timedelta(days=1)
    if ship_status == "delivered":
        delivered_at = created_at + timedelta(days=delivered_offset_days or rng.randint(4, 10))
        if delivered_at > now:
            delivered_at = now - timedelta(days=1)
        actual_delivery = delivered_at
        if customer_received is None:
            customer_received = True

    order = OrderRecord(
        id=rng.uuid4(),
        public_id=f"ORD-{order_index:05d}",
        customer_id=customer.id,
        status=status,
        total_amount=line_total,
        currency=company["company"]["currency"],
        created_at=created_at,
        estimated_delivery=estimated,
        actual_delivery=actual_delivery,
    )
    item = OrderItemRecord(
        id=rng.uuid4(),
        public_id=f"ITM-{item_index:05d}",
        order_id=order.id,
        product_id=product.id,
        quantity=quantity,
        unit_price=product.unit_price,
        line_total=line_total,
    )
    world.orders.append(order)
    world.order_items.append(item)

    for _ in range(failed_payments):
        world.payments.append(
            PaymentRecord(
                id=rng.uuid4(),
                public_id=f"PAY-{pay_index:05d}",
                order_id=order.id,
                status="failed",
                amount=line_total,
                payment_method=method,
                transaction_id=f"TXN-{rng.uuid4().hex[:12].upper()}",
                created_at=created_at - timedelta(hours=2),
            )
        )
        pay_index += 1

    paid_status = "paid" if status != "pending" else "pending"
    if status == "cancelled" and rng.random() < 0.3:
        paid_status = "failed"

    first_payment = PaymentRecord(
        id=rng.uuid4(),
        public_id=f"PAY-{pay_index:05d}",
        order_id=order.id,
        status=paid_status,
        amount=line_total,
        payment_method=method,
        transaction_id=f"TXN-{rng.uuid4().hex[:12].upper()}",
        created_at=created_at,
    )
    world.payments.append(first_payment)
    pay_index += 1

    if extra_paid_payment:
        world.payments.append(
            PaymentRecord(
                id=rng.uuid4(),
                public_id=f"PAY-{pay_index:05d}",
                order_id=order.id,
                status="paid",
                amount=line_total,
                payment_method=(
                    second_payment_method
                    if second_payment_method in allowed_methods
                    else method
                ),
                transaction_id=f"TXN-{rng.uuid4().hex[:12].upper()}",
                created_at=created_at + timedelta(minutes=8),
            )
        )

    if ship_status:
        world.shipments.append(
            ShipmentRecord(
                id=rng.uuid4(),
                public_id=f"SHP-{ship_index:05d}",
                order_id=order.id,
                carrier=rng.choice(carriers),
                tracking_code=f"TRK{rng.uuid4().hex[:10].upper()}",
                status=ship_status,
                shipped_at=shipped_at,
                estimated_delivery=estimated,
                delivered_at=delivered_at,
                customer_received=customer_received,
            )
        )
    return order


def add_ticket(
    world: World,
    rng: SeededRNG,
    now: datetime,
    customer: CustomerRecord,
    order: OrderRecord | None,
    subject: str,
    description: str,
    intent: str,
) -> TicketRecord:
    """Append a support ticket."""
    ticket = TicketRecord(
        id=rng.uuid4(),
        customer_id=customer.id,
        order_id=order.id if order else None,
        subject=subject,
        description=description,
        status="open",
        intent=intent,
        created_at=now - timedelta(hours=rng.randint(1, 48)),
    )
    world.tickets.append(ticket)
    return ticket


def fill_happy_path(
    world: World,
    rng: SeededRNG,
    now: datetime,
    company: dict[str, Any],
    target_customers: int,
    target_orders: int,
) -> None:
    """Fill remaining customers and orders with coherent happy-path data."""
    while len(world.customers) < target_customers:
        roll = rng.random()
        status = "active"
        if roll > 0.98:
            status = "closed"
        elif roll > 0.92:
            status = "suspended"
        world.customers.append(
            build_customer(world, rng, now, index=len(world.customers) + 1, status=status)
        )

    owned = {customer.id: 0 for customer in world.customers}
    for order in world.orders:
        owned[order.customer_id] = owned.get(order.customer_id, 0) + 1

    def _add_random_order(customer: CustomerRecord) -> None:
        product = rng.choice(world.products)
        status = _weighted_order_status(rng)
        created_at = now - timedelta(days=rng.randint(2, 80))
        add_order_bundle(
            world,
            rng,
            now,
            company,
            customer,
            product,
            status=status,
            created_at=created_at,
        )
        owned[customer.id] = owned.get(customer.id, 0) + 1

    for customer in world.customers:
        if owned.get(customer.id, 0) == 0:
            _add_random_order(customer)

    while len(world.orders) < target_orders:
        eligible = [
            item
            for item in world.customers
            if item.email.lower() != DEMO_SHOWCASE_EMAIL
        ]
        customer = rng.choice(eligible or world.customers)
        _add_random_order(customer)


def assign_public_ids(world: World) -> None:
    """Rewrite sequential public_ids after the full graph is assembled."""
    for index, product in enumerate(world.products, start=1):
        product.public_id = f"PRD-{index:05d}"
    for index, customer in enumerate(world.customers, start=1):
        customer.public_id = f"CUST-{index:05d}"
    for index, order in enumerate(world.orders, start=1):
        order.public_id = f"ORD-{index + 1000:05d}"
    for index, item in enumerate(world.order_items, start=1):
        item.public_id = f"ITM-{index:05d}"
    for index, payment in enumerate(world.payments, start=1):
        payment.public_id = f"PAY-{index:05d}"
    for index, shipment in enumerate(world.shipments, start=1):
        shipment.public_id = f"SHP-{index:05d}"
    for index, ret in enumerate(world.returns, start=1):
        ret.public_id = f"RET-{index:05d}"
    for index, refund in enumerate(world.refunds, start=1):
        refund.public_id = f"RFD-{index:05d}"


def assert_integrity(world: World) -> None:
    """Raise if the generated graph is internally inconsistent."""
    products = {item.id: item for item in world.products}
    customers = {item.id: item for item in world.customers}
    orders = {item.id: item for item in world.orders}
    items_by_order: dict[Any, list[OrderItemRecord]] = {}
    for item in world.order_items:
        if item.order_id not in orders:
            raise AssertionError(f"order_item {item.public_id} missing order")
        if item.product_id not in products:
            raise AssertionError(f"order_item {item.public_id} missing product")
        items_by_order.setdefault(item.order_id, []).append(item)
        expected = (item.unit_price * item.quantity).quantize(Decimal("0.01"))
        if item.line_total != expected:
            raise AssertionError(f"line_total mismatch for {item.public_id}")

    for order in world.orders:
        if order.customer_id not in customers:
            raise AssertionError(f"order {order.public_id} missing customer")
        lines = items_by_order.get(order.id, [])
        total = sum((line.line_total for line in lines), Decimal("0.00"))
        if abs(total - order.total_amount) > Decimal("0.01"):
            raise AssertionError(f"order total mismatch for {order.public_id}")

    payments_by_order: dict[Any, list[PaymentRecord]] = {}
    for payment in world.payments:
        if payment.order_id not in orders:
            raise AssertionError(f"payment {payment.public_id} missing order")
        payments_by_order.setdefault(payment.order_id, []).append(payment)

    scenario_kinds = {item.id for item in world.scenarios if item.kind == "double_payment"}
    double_orders = {
        item.order_id for item in world.scenarios if item.kind == "double_payment" and item.order_id
    }
    for order in world.orders:
        paid = [
            payment
            for payment in payments_by_order.get(order.id, [])
            if payment.status == "paid"
        ]
        if order.id in double_orders:
            if len(paid) < 2:
                raise AssertionError(f"double payment order {order.public_id} lacks two paid rows")
            continue
        if order.status in {"paid", "processing", "shipped", "delivered", "returned"}:
            paid_sum = sum((payment.amount for payment in paid), Decimal("0.00"))
            if paid and abs(paid_sum - order.total_amount) > Decimal("0.01") and len(paid) == 1:
                pass

    shipments_by_order = {item.order_id: item for item in world.shipments}
    for shipment in world.shipments:
        order = orders[shipment.order_id]
        if shipment.shipped_at and shipment.shipped_at < order.created_at:
            raise AssertionError(f"shipped_at before order for {shipment.public_id}")
        if shipment.delivered_at and shipment.shipped_at and shipment.delivered_at < shipment.shipped_at:
            raise AssertionError(f"delivered_at before shipped_at for {shipment.public_id}")

    for ret in world.returns:
        if ret.order_id not in orders or ret.customer_id not in customers:
            raise AssertionError(f"return {ret.public_id} missing parent")
        if orders[ret.order_id].customer_id != ret.customer_id:
            raise AssertionError(f"return {ret.public_id} customer mismatch")
        order = orders[ret.order_id]
        if order.status not in {"shipped", "delivered", "returned"}:
            raise AssertionError(f"return {ret.public_id} on non-shipped order")

    for refund in world.refunds:
        order = orders[refund.order_id]
        paid_sum = sum(
            (
                payment.amount
                for payment in payments_by_order.get(order.id, [])
                if payment.status == "paid"
            ),
            Decimal("0.00"),
        )
        if refund.amount > paid_sum + Decimal("0.01"):
            raise AssertionError(f"refund {refund.public_id} exceeds paid amount")

    for ticket in world.tickets:
        if ticket.customer_id not in customers:
            raise AssertionError("ticket missing customer")
        if ticket.order_id and ticket.order_id not in orders:
            raise AssertionError("ticket missing order")
        if ticket.order_id and orders[ticket.order_id].customer_id != ticket.customer_id:
            raise AssertionError("ticket customer/order mismatch")

    orders_by_customer = {item.id: 0 for item in world.customers}
    for order in world.orders:
        orders_by_customer[order.customer_id] = orders_by_customer.get(order.customer_id, 0) + 1
    missing = [item.public_id for item in world.customers if orders_by_customer.get(item.id, 0) < 1]
    if missing:
        raise AssertionError(f"customers without orders: {missing}")

    emails = [item.email.lower() for item in world.customers]
    if len(emails) != len(set(emails)):
        raise AssertionError("duplicate customer emails")

    _ = (scenario_kinds, shipments_by_order)
