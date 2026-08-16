"""Labeled synthetic scenario pointers for evaluation."""

import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.customer import Customer
from app.models.order import Order
from app.persistence import Base


class SyntheticScenario(Base):
    """Stable labeled pointer from an evaluation scenario id to operational rows."""

    __tablename__ = "synthetic_scenarios"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(64), index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id"),
        index=True,
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id"),
        nullable=True,
        index=True,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    user_message_pt: Mapped[str] = mapped_column(Text)
    expected_intent: Mapped[str] = mapped_column(String(32))
    expected_resolution: Mapped[str] = mapped_column(String(64))
    requires_human: Mapped[bool] = mapped_column(Boolean, default=False)

    customer: Mapped[Customer] = relationship()
    order: Mapped[Order | None] = relationship()
