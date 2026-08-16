"""Return request ORM model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.enums import InspectionStatus, ReturnReason, ReturnStatus
from app.persistence import Base

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.order import Order
    from app.models.refund import Refund


class ReturnRequest(Base):
    """Customer return request against an order."""

    __tablename__ = "returns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id"),
        index=True,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id"),
        index=True,
    )
    reason: Mapped[ReturnReason] = mapped_column(
        Enum(ReturnReason, name="return_reason", values_callable=lambda x: [e.value for e in x]),
    )
    status: Mapped[ReturnStatus] = mapped_column(
        Enum(ReturnStatus, name="return_status", values_callable=lambda x: [e.value for e in x]),
    )
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    inspection_status: Mapped[InspectionStatus] = mapped_column(
        Enum(
            InspectionStatus,
            name="inspection_status",
            values_callable=lambda x: [e.value for e in x],
        ),
    )

    order: Mapped["Order"] = relationship(back_populates="returns")
    customer: Mapped["Customer"] = relationship()
    refunds: Mapped[list["Refund"]] = relationship(back_populates="return_request")
