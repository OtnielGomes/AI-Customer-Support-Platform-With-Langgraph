"""Refund ORM model."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.enums import RefundStatus
from app.persistence import Base

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.payment import Payment
    from app.models.return_request import ReturnRequest


class Refund(Base):
    """Refund request or executed reversal against an order/payment."""

    __tablename__ = "refunds"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id"),
        index=True,
    )
    return_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("returns.id"),
        nullable=True,
    )
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payments.id"),
        nullable=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[RefundStatus] = mapped_column(
        Enum(RefundStatus, name="refund_status", values_callable=lambda x: [e.value for e in x]),
    )
    reason: Mapped[str] = mapped_column(String(255))
    requires_human_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order: Mapped["Order"] = relationship(back_populates="refunds")
    return_request: Mapped["ReturnRequest | None"] = relationship(back_populates="refunds")
    payment: Mapped["Payment | None"] = relationship(back_populates="refunds")
