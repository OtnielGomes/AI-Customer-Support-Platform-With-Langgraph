"""NexaCommerce operational schema: products, orders, payments, shipments, returns, refunds."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_nexa_operational"
down_revision: Union[str, None] = "002_agent_runs_and_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add operational tables and extend customers/tickets."""
    customer_tier = postgresql.ENUM(
        "standard",
        "silver",
        "gold",
        "enterprise",
        name="customer_tier",
    )
    account_status = postgresql.ENUM("active", "suspended", "closed", name="account_status")
    customer_tier.create(op.get_bind(), checkfirst=True)
    account_status.create(op.get_bind(), checkfirst=True)

    op.add_column("customers", sa.Column("public_id", sa.String(length=32), nullable=True))
    op.add_column("customers", sa.Column("phone", sa.String(length=32), nullable=True))
    op.add_column(
        "customers",
        sa.Column("customer_tier", customer_tier, server_default="standard", nullable=False),
    )
    op.add_column(
        "customers",
        sa.Column("account_status", account_status, server_default="active", nullable=False),
    )
    op.execute(
        "UPDATE customers SET public_id = 'CUST-' || UPPER(SUBSTRING(REPLACE(id::text, '-', ''), 1, 8)) "
        "WHERE public_id IS NULL"
    )
    op.alter_column("customers", "public_id", nullable=False)
    op.create_index("ix_customers_public_id", "customers", ["public_id"], unique=True)

    op.create_table(
        "products",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "smartphones",
                "laptops",
                "monitors",
                "headphones",
                "keyboards",
                "accessories",
                name="product_category",
            ),
            nullable=False,
        ),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("final_sale", sa.Boolean(), nullable=False),
        sa.Column("warranty_days", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("sku"),
    )
    op.create_index("ix_products_public_id", "products", ["public_id"])
    op.create_index("ix_products_sku", "products", ["sku"])

    op.create_table(
        "orders",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "paid",
                "processing",
                "shipped",
                "delivered",
                "cancelled",
                "returned",
                name="order_status",
            ),
            nullable=False,
        ),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("estimated_delivery", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_delivery", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
    )
    op.create_index("ix_orders_public_id", "orders", ["public_id"])
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_index("ix_orders_created_at", "orders", ["created_at"])

    op.create_table(
        "order_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
    )
    op.create_index("ix_order_items_public_id", "order_items", ["public_id"])
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])
    op.create_index("ix_order_items_product_id", "order_items", ["product_id"])

    op.create_table(
        "payments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "authorized",
                "paid",
                "failed",
                "refunded",
                "partially_refunded",
                name="payment_status",
            ),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "payment_method",
            sa.Enum("credit_card", "debit_card", "pix", "boleto", name="payment_method"),
            nullable=False,
        ),
        sa.Column("transaction_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("transaction_id"),
    )
    op.create_index("ix_payments_public_id", "payments", ["public_id"])
    op.create_index("ix_payments_order_id", "payments", ["order_id"])
    op.create_index("ix_payments_status", "payments", ["status"])

    op.create_table(
        "shipments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("carrier", sa.String(length=64), nullable=False),
        sa.Column("tracking_code", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "processing",
                "shipped",
                "in_transit",
                "out_for_delivery",
                "delivered",
                "delayed",
                "lost",
                name="shipment_status",
            ),
            nullable=False,
        ),
        sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("estimated_delivery", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("customer_received", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("order_id"),
        sa.UniqueConstraint("tracking_code"),
    )
    op.create_index("ix_shipments_public_id", "shipments", ["public_id"])
    op.create_index("ix_shipments_tracking_code", "shipments", ["tracking_code"])
    op.create_index("ix_shipments_status", "shipments", ["status"])

    op.create_table(
        "returns",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column(
            "reason",
            sa.Enum(
                "defective_product",
                "wrong_item",
                "customer_preference",
                "missing_parts",
                "other",
                name="return_reason",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "requested",
                "pending_inspection",
                "approved",
                "rejected",
                "completed",
                "cancelled",
                name="return_status",
            ),
            nullable=False,
        ),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "inspection_status",
            sa.Enum("pending", "passed", "failed", "not_required", name="inspection_status"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
    )
    op.create_index("ix_returns_public_id", "returns", ["public_id"])
    op.create_index("ix_returns_order_id", "returns", ["order_id"])

    op.create_table(
        "refunds",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("return_id", sa.UUID(), nullable=True),
        sa.Column("payment_id", sa.UUID(), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "requested",
                "pending_approval",
                "approved",
                "executed",
                "denied",
                name="refund_status",
            ),
            nullable=False,
        ),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("requires_human_approval", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["return_id"], ["returns.id"]),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
    )
    op.create_index("ix_refunds_public_id", "refunds", ["public_id"])
    op.create_index("ix_refunds_order_id", "refunds", ["order_id"])

    op.add_column("tickets", sa.Column("order_id", sa.UUID(), nullable=True))
    op.create_index("ix_tickets_order_id", "tickets", ["order_id"])
    op.create_foreign_key("fk_tickets_order_id", "tickets", "orders", ["order_id"], ["id"])

    op.create_table(
        "synthetic_scenarios",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("user_message_pt", sa.Text(), nullable=False),
        sa.Column("expected_intent", sa.String(length=32), nullable=False),
        sa.Column("expected_resolution", sa.String(length=64), nullable=False),
        sa.Column("requires_human", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_synthetic_scenarios_kind", "synthetic_scenarios", ["kind"])
    op.create_index("ix_synthetic_scenarios_customer_id", "synthetic_scenarios", ["customer_id"])
    op.create_index("ix_synthetic_scenarios_order_id", "synthetic_scenarios", ["order_id"])


def downgrade() -> None:
    """Drop operational tables and customer/ticket extensions."""
    op.drop_index("ix_synthetic_scenarios_order_id", table_name="synthetic_scenarios")
    op.drop_index("ix_synthetic_scenarios_customer_id", table_name="synthetic_scenarios")
    op.drop_index("ix_synthetic_scenarios_kind", table_name="synthetic_scenarios")
    op.drop_table("synthetic_scenarios")

    op.drop_constraint("fk_tickets_order_id", "tickets", type_="foreignkey")
    op.drop_index("ix_tickets_order_id", table_name="tickets")
    op.drop_column("tickets", "order_id")

    op.drop_index("ix_refunds_order_id", table_name="refunds")
    op.drop_index("ix_refunds_public_id", table_name="refunds")
    op.drop_table("refunds")
    op.drop_index("ix_returns_order_id", table_name="returns")
    op.drop_index("ix_returns_public_id", table_name="returns")
    op.drop_table("returns")
    op.drop_index("ix_shipments_status", table_name="shipments")
    op.drop_index("ix_shipments_tracking_code", table_name="shipments")
    op.drop_index("ix_shipments_public_id", table_name="shipments")
    op.drop_table("shipments")
    op.drop_index("ix_payments_status", table_name="payments")
    op.drop_index("ix_payments_order_id", table_name="payments")
    op.drop_index("ix_payments_public_id", table_name="payments")
    op.drop_table("payments")
    op.drop_index("ix_order_items_product_id", table_name="order_items")
    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_index("ix_order_items_public_id", table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("ix_orders_created_at", table_name="orders")
    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_index("ix_orders_customer_id", table_name="orders")
    op.drop_index("ix_orders_public_id", table_name="orders")
    op.drop_table("orders")
    op.drop_index("ix_products_sku", table_name="products")
    op.drop_index("ix_products_public_id", table_name="products")
    op.drop_table("products")

    op.drop_index("ix_customers_public_id", table_name="customers")
    op.drop_column("customers", "account_status")
    op.drop_column("customers", "customer_tier")
    op.drop_column("customers", "phone")
    op.drop_column("customers", "public_id")

    op.execute("DROP TYPE IF EXISTS refund_status")
    op.execute("DROP TYPE IF EXISTS inspection_status")
    op.execute("DROP TYPE IF EXISTS return_status")
    op.execute("DROP TYPE IF EXISTS return_reason")
    op.execute("DROP TYPE IF EXISTS shipment_status")
    op.execute("DROP TYPE IF EXISTS payment_method")
    op.execute("DROP TYPE IF EXISTS payment_status")
    op.execute("DROP TYPE IF EXISTS order_status")
    op.execute("DROP TYPE IF EXISTS product_category")
    op.execute("DROP TYPE IF EXISTS account_status")
    op.execute("DROP TYPE IF EXISTS customer_tier")
