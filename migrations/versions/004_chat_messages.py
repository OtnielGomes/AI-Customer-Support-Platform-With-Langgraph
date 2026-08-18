"""Chat messages table and ticket inbox columns."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_chat_messages"
down_revision: Union[str, None] = "003_nexa_operational"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add ticket_messages and inbox columns on tickets."""
    message_role = postgresql.ENUM(
        "customer",
        "assistant",
        "human_agent",
        "system",
        name="ticket_message_role",
    )
    message_role.create(op.get_bind(), checkfirst=True)

    op.add_column("tickets", sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tickets", sa.Column("assigned_agent", sa.String(length=255), nullable=True))
    op.create_index("ix_tickets_last_message_at", "tickets", ["last_message_at"])
    op.execute("UPDATE tickets SET last_message_at = COALESCE(updated_at, created_at)")

    op.create_table(
        "ticket_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM(
                "customer",
                "assistant",
                "human_agent",
                "system",
                name="ticket_message_role",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"]),
    )
    op.create_index("ix_ticket_messages_ticket_id", "ticket_messages", ["ticket_id"])
    op.create_index("ix_ticket_messages_agent_run_id", "ticket_messages", ["agent_run_id"])
    op.create_index("ix_ticket_messages_created_at", "ticket_messages", ["created_at"])
    op.execute(
        """
        INSERT INTO ticket_messages (id, ticket_id, role, content, created_at)
        SELECT gen_random_uuid(), id, 'customer', description, created_at
        FROM tickets
        WHERE description IS NOT NULL AND description <> ''
        """
    )


def downgrade() -> None:
    """Drop chat message storage."""
    op.drop_index("ix_ticket_messages_created_at", table_name="ticket_messages")
    op.drop_index("ix_ticket_messages_agent_run_id", table_name="ticket_messages")
    op.drop_index("ix_ticket_messages_ticket_id", table_name="ticket_messages")
    op.drop_table("ticket_messages")
    op.drop_index("ix_tickets_last_message_at", table_name="tickets")
    op.drop_column("tickets", "assigned_agent")
    op.drop_column("tickets", "last_message_at")
    message_role = postgresql.ENUM(
        "customer",
        "assistant",
        "human_agent",
        "system",
        name="ticket_message_role",
    )
    message_role.drop(op.get_bind(), checkfirst=True)
