"""Shipment ORM model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.enums import ShipmentStatus
from app.persistence import Base

if TYPE_CHECKING:
    from app.models.order import Order


class Shipment(Base):
    """Carrier shipment for an order (one per order in v1)."""

    __tablename__ = "shipments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id"),
        unique=True,
        index=True,
    )
    carrier: Mapped[str] = mapped_column(String(64))
    tracking_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[ShipmentStatus] = mapped_column(
        Enum(
            ShipmentStatus,
            name="shipment_status",
            values_callable=lambda x: [e.value for e in x],
        ),
        index=True,
    )
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_delivery: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    customer_received: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    order: Mapped["Order"] = relationship(back_populates="shipment")
