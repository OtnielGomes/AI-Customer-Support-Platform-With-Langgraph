"""Agent runs, events, and ticket list indexes."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_agent_runs_and_indexes"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create agent_runs/agent_events and ticket listing indexes."""
    op.create_index("ix_tickets_status", "tickets", ["status"])
    op.create_index("ix_tickets_created_at", "tickets", ["created_at"])
    op.create_index("ix_tickets_escalated_at", "tickets", ["escalated_at"])

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("ticket_id", sa.UUID(), nullable=False),
        sa.Column("thread_id", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "running",
                "completed",
                "awaiting_human",
                "failed",
                name="agent_run_status",
            ),
            nullable=False,
        ),
        sa.Column("intent", sa.String(length=50), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("escalated", sa.Boolean(), nullable=False),
        sa.Column("total_latency_ms", sa.Float(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_runs_ticket_id", "agent_runs", ["ticket_id"])
    op.create_index("ix_agent_runs_thread_id", "agent_runs", ["thread_id"])

    op.create_table(
        "agent_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column(
            "event_type",
            sa.Enum("node", "tool", "llm", "retrieval", "guardrail", name="agent_event_type"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("input", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("output", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_events_run_id", "agent_events", ["run_id"])
    op.create_index("ix_agent_events_event_type", "agent_events", ["event_type"])


def downgrade() -> None:
    """Drop agent tables and ticket listing indexes."""
    op.drop_index("ix_agent_events_event_type", table_name="agent_events")
    op.drop_index("ix_agent_events_run_id", table_name="agent_events")
    op.drop_table("agent_events")
    op.drop_index("ix_agent_runs_thread_id", table_name="agent_runs")
    op.drop_index("ix_agent_runs_ticket_id", table_name="agent_runs")
    op.drop_table("agent_runs")
    op.drop_index("ix_tickets_escalated_at", table_name="tickets")
    op.drop_index("ix_tickets_created_at", table_name="tickets")
    op.drop_index("ix_tickets_status", table_name="tickets")
    op.execute("DROP TYPE IF EXISTS agent_event_type")
    op.execute("DROP TYPE IF EXISTS agent_run_status")
