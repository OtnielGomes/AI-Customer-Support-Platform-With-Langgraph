"""Initial schema with pgvector."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create tables and vector index."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "customers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_customers_email", "customers", ["email"])

    op.create_table(
        "tickets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("open", "in_progress", "resolved", "escalated", "closed", name="ticket_status"),
            nullable=False,
        ),
        sa.Column(
            "intent",
            sa.Enum("billing", "logistics", "account", "unknown", name="ticket_intent"),
            nullable=True,
        ),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tickets_customer_id", "tickets", ["customer_id"])

    op.create_table(
        "resolutions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("ticket_id", sa.UUID(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("escalated", sa.Boolean(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_id"),
    )
    op.create_index("ix_resolutions_ticket_id", "resolutions", ["ticket_id"])

    op.create_table(
        "kb_chunks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("source_path", sa.String(length=500), nullable=False),
        sa.Column("domain", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_hash"),
    )
    op.create_index("ix_kb_chunks_content_hash", "kb_chunks", ["content_hash"])
    op.create_index("ix_kb_chunks_domain", "kb_chunks", ["domain"])
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_kb_chunks_embedding_hnsw ON kb_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    """Drop all tables."""
    op.drop_index("ix_kb_chunks_embedding_hnsw", table_name="kb_chunks")
    op.drop_index("ix_kb_chunks_domain", table_name="kb_chunks")
    op.drop_index("ix_kb_chunks_content_hash", table_name="kb_chunks")
    op.drop_table("kb_chunks")
    op.drop_index("ix_resolutions_ticket_id", table_name="resolutions")
    op.drop_table("resolutions")
    op.drop_index("ix_tickets_customer_id", table_name="tickets")
    op.drop_table("tickets")
    op.drop_index("ix_customers_email", table_name="customers")
    op.drop_table("customers")
    op.execute("DROP TYPE IF EXISTS ticket_status")
    op.execute("DROP TYPE IF EXISTS ticket_intent")
