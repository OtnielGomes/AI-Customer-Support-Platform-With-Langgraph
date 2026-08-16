"""Payment ORM model."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.enums import PaymentMethod, PaymentStatus
from app.persistence import Base

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.refund import Refund


class Payment(Base):
    """Payment attempt or capture against an order."""

    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id"),
        index=True,
    )
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status", values_callable=lambda x: [e.value for e in x]),
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method", values_callable=lambda x: [e.value for e in x]),
    )
    transaction_id: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order: Mapped["Order"] = relationship(back_populates="payments")
    refunds: Mapped[list["Refund"]] = relationship(back_populates="payment")
